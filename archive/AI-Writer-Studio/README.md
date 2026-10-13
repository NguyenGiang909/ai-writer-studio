# AI Writer Studio — mã nguồn Site

Trang tĩnh, mở `dist/index.html` trong trình duyệt để xem. Để triển khai lên hosting tĩnh, phục vụ thư mục `dist/`.

Phần Tài khoản & Credit và Kết nối API hiện là giao diện chuẩn bị: hồ sơ và lựa chọn model lưu trong localStorage của trình duyệt; API key chỉ giữ trong tab cho đến khi tải lại, chưa gọi API. Credit hiển thị 0 và chưa có giao dịch, đăng nhập hay thanh toán. Cần backend và xác thực trước khi dùng API key, đồng bộ tài khoản hoặc tính credit thật.

`dist/index.html` chứa mã HTML, CSS và JavaScript của ứng dụng. `.openai/hosting.json` là cấu hình Sites.
