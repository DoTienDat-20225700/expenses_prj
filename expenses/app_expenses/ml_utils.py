import os
import joblib
import pandas as pd
from django.conf import settings
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from .models import Expense

def get_model_path(user):
    """Tạo đường dẫn file model riêng cho từng user"""
    # File sẽ có tên dạng: expense_model_1.pkl (với 1 là ID của user)
    filename = f'expense_model_{user.id}.pkl'
    return os.path.join(settings.BASE_DIR, filename)

def train_model(user):
    """Hàm huấn luyện AI (tối ưu memory và query bằng values_list)"""    
    # Chỉ lấy các bản ghi có description và category trực tiếp từ DB dưới dạng raw tuple
    raw_data = list(
        Expense.objects.filter(
            user=user,
            category__isnull=False,
        ).exclude(
            description__isnull=True
        ).exclude(
            description=''
        ).values_list('description', 'category_id')
    )
    
    # Cần ít nhất 3 mẫu dữ liệu để học
    if len(raw_data) < 3:
        return None

    df = pd.DataFrame(raw_data, columns=['text', 'label'])

    model = make_pipeline(CountVectorizer(), MultinomialNB())
    model.fit(df['text'], df['label'])
    
    # Lưu file model riêng của user đó
    model_path = get_model_path(user)
    joblib.dump(model, model_path)
    return model

def predict_category(description, user):
    """Hàm dự đoán"""
    if not description:
        return None

    model_path = get_model_path(user)

    # Tải model
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
        except Exception as e:
            return None
    else:
        # Nếu chưa có model thì thử huấn luyện ngay
        model = train_model(user)
    
    if model is None:
        return None

    try:
        predicted_id = model.predict([description])[0]
        # Lấy xác suất tự tin (Confidence)
        probability = model.predict_proba([description]).max()
        
        # Chỉ đề xuất nếu AI khá chắc chắn (> 30%)
        if probability > 0.3:
            return int(predicted_id)
        else:
            return None
    except Exception as e:
        return None