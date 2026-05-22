import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any

from python.frontend.core_types import BaseEngine

class BridgedStateDict(dict):
    """
    A bridged dictionary that prevents the TUI from marking optional parameters 
    as '[Missing]' and striking them out.
    
    Because kernel parameters are flags that are inherently 'optional' (their absence 
    just implies the kernel's default behavior), they should always be treated as 
    available and fully editable by the UI.
    """
    def __contains__(self, key: Any) -> bool:
        return True

    def __getitem__(self, key: Any) -> Any:
        return super().get(key, "unset")

    def get(self, key: Any, default: Any = None) -> Any:
        # Override get() as well, since CPython dict.get bypasses __getitem__
        return super().get(key, "unset")


class CmdlineEngine(BaseEngine):
    """
    Bridged Intelligent engine for /etc/kernel/cmdline and similar kernel parameter files.
    
    Features:
    - Bridged State: Prevents optional parameters from rendering as missing/broken.
    - Type-Aware AST: Strictly separates boolean flags (rw) from KV pairs (root=xyz).
    - Token-Preservation: Uses regex to preserve the exact spacing and order of all arguments.
    - Duplicate Key Tracking: Properly indexes duplicate arguments (like multiple console=ttyS0).
    - Atomic Commits: Crucial for boot-critical files to prevent a corrupted state during power loss.
    """
    
    def __init__(self, config_path: str = "/etc/kernel/cmdline"):
        self.config_path = Path(config_path).expanduser().resolve()
        self.cache: BridgedStateDict = BridgedStateDict()
        self.file_mtime: float = 0.0

    @property
    def target_path(self) -> str:
        return str(self.config_path)

    def load_state(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return BridgedStateDict()

        self.file_mtime = self.config_path.stat().st_mtime
        self.cache = BridgedStateDict()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Advanced tokenization respecting single/double quotes to prevent splitting quoted spaces
            tokens = re.split(r'((?:[^\s"\']|"[^"]*"|\'[^\']*\')+)', content)
            args = [t for t in tokens if t.strip()]
            counts = {}
            
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                else:
                    k, v = arg, "true" # Represent standalone flags as boolean true
                    
                counts[k] = counts.get(k, 0) + 1
                count = counts[k]
                
                # Expose the first instance standardly, but all instances with explicit index
                if count == 1:
                    self.cache[f"DEFAULT/{k}"] = v
                self.cache[f"DEFAULT/{k}:{count}"] = v
                
                # Smart Sub-Key parsing for complex comma-separated values (e.g. rootflags=subvol=/@,noatime)
                if "," in v and count == 1 and not (v.startswith('"') or v.startswith("'")):
                    sub_items = v.split(",")
                    for item in sub_items:
                        if "=" in item:
                            sk, sv = item.split("=", 1)
                            self.cache[f"DEFAULT/{k}.{sk}"] = sv
                        else:
                            self.cache[f"DEFAULT/{k}.{item}"] = "true"

        except (OSError, IOError) as e:
            print(f"Failed to read cmdline config {self.config_path}: {e}")
            
        return self.cache

    def write_value(self, target_key: str, target_scope: str, new_value: str, item_type: str = "string") -> tuple[bool, str, str]:
        return self.write_batch([(target_key, target_scope, new_value, item_type)])

    def write_batch(self, changes: list[tuple[str, str, str, str]]) -> tuple[bool, str, str]:
        if not changes:
            return True, "No pending changes.", ""
            
        if self.config_path.exists():
            current_mtime = self.config_path.stat().st_mtime
            if current_mtime > self.file_mtime:
                return False, f"File {self.config_path.name} modified externally. Reload required.", ""

        # Map using precise item types to prevent string/bool coercion bugs
        changes_dict = {(scope, key): (val, itype) for key, scope, val, itype in changes}
        applied_commits = set()
        
        try:
            content = ""
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
            # Tokenize preserving all exact whitespace and quotes
            tokens = re.split(r'((?:[^\s"\']|"[^"]*"|\'[^\']*\')+)', content)
            out_tokens = []
            counts = {}
            
            for t in tokens:
                if not t.strip():
                    out_tokens.append(t)
                    continue
                    
                if "=" in t:
                    k, v = t.split("=", 1)
                else:
                    k = t
                    v = "true"
                    
                counts[k] = counts.get(k, 0) + 1
                count = counts[k]
                
                lookup_exact = ("DEFAULT", f"{k}:{count}")
                lookup_base = ("DEFAULT", k)
                
                target_val = None
                target_itype = None
                matched_lookup = None
                
                if lookup_exact in changes_dict:
                    target_val, target_itype = changes_dict[lookup_exact]
                    matched_lookup = lookup_exact
                elif count == 1 and lookup_base in changes_dict:
                    target_val, target_itype = changes_dict[lookup_base]
                    matched_lookup = lookup_base
                    
                if target_val is not None:
                    applied_commits.add(matched_lookup)
                    val_str = str(target_val)
                    val_lower = val_str.lower()
                    
                    # Strictly evaluate based on item type
                    if val_str in ("__DELETE__", "unset", "") or (target_itype == "bool" and val_lower == "false"):
                        # Discard token to cleanly delete the parameter from the file
                        pass
                    elif target_itype == "bool" and val_lower == "true":
                        # Write as a standalone flag
                        out_tokens.append(k)
                    else:
                        # Write as Key-Value
                        out_tokens.append(f"{k}={val_str}")
                else:
                    out_tokens.append(t)
                    
            # Handle brand new keys appended to the end
            missing_changes = set(changes_dict.keys()) - applied_commits
            for scope, key_raw in missing_changes:
                val, target_itype = changes_dict[(scope, key_raw)]
                val_str = str(val)
                val_lower = val_str.lower()
                
                # Prevent appending 'unset' or 'false' markers 
                if val_str in ("__DELETE__", "unset", "") or (target_itype == "bool" and val_lower == "false"):
                    continue
                    
                actual_key = key_raw.split(":")[0] if ":" in key_raw else key_raw
                
                # Ensure spacing before appending
                needs_space = False
                for tk in reversed(out_tokens):
                    if tk:
                        needs_space = bool(tk.strip())
                        break
                if needs_space:
                    out_tokens.append(" ")
                    
                if target_itype == "bool" and val_lower == "true":
                    out_tokens.append(actual_key)
                else:
                    out_tokens.append(f"{actual_key}={val_str}")
                    
                applied_commits.add((scope, key_raw))
                
            # Ensure safe output without destroying user's exact spacing
            final_content = "".join(out_tokens).strip() + "\n"
            
            # --- Safe Atomic File Commit ---
            success = False
            status_msg = "Failed"
            temp_file_path = None
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', dir=self.config_path.parent) as tf:
                temp_file_path = Path(tf.name)
                tf.write(final_content)
                
            if self.config_path.exists():
                try: temp_file_path.chmod(stat.S_IMODE(self.config_path.stat().st_mode))
                except OSError: pass
                    
            os.replace(temp_file_path, self.config_path)
            self.file_mtime = self.config_path.stat().st_mtime
            success = True
            
        except OSError as e:
            return False, f"Atomic commit failed: {e}", ""
        finally:
            if 'temp_file_path' in locals() and temp_file_path and temp_file_path.exists() and not success:
                try: temp_file_path.unlink()
                except OSError: pass

        if success:
            return True, f"Successfully batched {len(applied_commits)} commits.", ""
            
        return False, status_msg, ""
