from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    CommonPasswordValidator,
    NumericPasswordValidator,
)

# 1. Validator độ dài tối thiểu
class VietnameseMinimumLengthValidator(MinimumLengthValidator):
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                f"Mật khẩu quá ngắn. Phải có ít nhất {self.min_length} ký tự.",
                code='password_too_short',
            )

    def get_help_text(self):
        return f"Mật khẩu phải có ít nhất {self.min_length} ký tự."

# 2. Validator mật khẩu toàn số
class VietnameseNumericPasswordValidator(NumericPasswordValidator):
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                "Mật khẩu không được chứa toàn bộ là số.",
                code='password_entirely_numeric',
            )

    def get_help_text(self):
        return "Mật khẩu không được chứa toàn bộ là số."

# 3. Validator mật khẩu phổ biến
class VietnameseCommonPasswordValidator(CommonPasswordValidator):
    def validate(self, password, user=None):
        # Chúng ta gọi lại hàm cha để nó tự kiểm tra danh sách 20,000 pass phổ biến
        # Nếu cha báo lỗi, ta bắt lỗi đó và ném ra lỗi tiếng Việt
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                "Mật khẩu này quá phổ biến (ví dụ: 123456, password...). Hãy chọn mật khẩu khó đoán hơn.",
                code='password_too_common',
            )

    def get_help_text(self):
        return "Mật khẩu không được quá phổ biến."