import os
import joblib
import pandas as pd
from django.conf import settings
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from .models import Expense

MODEL_PATH = os.path.join(settings.BASE_DIR, 'expense_model.pkl')

def train_model(user):
    """Hàm huấn luyện AI"""    
    expenses = Expense.objects.filter(user=user)
    
    data = []
    for e in expenses:
        if e.description and e.category:
            data.append({'text': e.description, 'label': e.category.id})
            
    # Nếu ít dữ liệu quá thì chưa học
    if len(data) < 3:
        return None

    df = pd.DataFrame(data)

    model = make_pipeline(CountVectorizer(), MultinomialNB())
    model.fit(df['text'], df['label'])
    
    # Lưu file
    joblib.dump(model, MODEL_PATH)
    return model

def predict_category(description, user):
    """Hàm dự đoán"""
    if not description:
        return None

    # Tải model
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
        except Exception as e:
            return None
    else:
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