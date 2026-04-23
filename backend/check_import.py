import sys
import traceback

sys.path.insert(0, ".")

log_lines = []

try:
    from app.main import app
    log_lines.append("SUCCESS - app loaded fine\n")
except Exception:
    tb = traceback.format_exc()
    log_lines.append(tb)

with open("check_result.txt", "w", encoding="utf-8") as f:
    f.writelines(log_lines)

print("done - see check_result.txt")
