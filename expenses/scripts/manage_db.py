import subprocess
import sys

def run_command(command):
    try:
        # Chạy lệnh terminal
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Thành công!")
        else:
            # Kiểm tra nếu service đã chạy
            if "already started" in result.stderr or "already started" in result.stdout:
                print("✅ MySQL đã chạy sẵn!")
            else:
                print("❌ Có lỗi xảy ra:")
                print(result.stderr if result.stderr else result.stdout)
    except subprocess.CalledProcessError:
        print("❌ Có lỗi xảy ra. Hãy kiểm tra lại MySQL.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python3 manage_db.py [start|stop|restart]")
        sys.exit(1)

    action = sys.argv[1]
    
    if action == "start":
        print("🚀 Đang bật MySQL Server...")
        run_command("brew services start mysql")
        
    elif action == "stop":
        print("🛑 Đang tắt MySQL Server...")
        run_command("brew services stop mysql")
        
    elif action == "restart":
        print("🔄 Đang khởi động lại MySQL Server...")
        run_command("brew services restart mysql")
        
    else:
        print("Lệnh không hợp lệ. Chỉ dùng: start, stop, restart")