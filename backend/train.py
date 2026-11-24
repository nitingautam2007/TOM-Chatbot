import os, pandas as pd, joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

df = pd.read_csv(DATA_PATH)  # columns: text,label
X_tr, X_te, y_tr, y_te = train_test_split(df.text, df.label, test_size=0.2,
                                          stratify=df.label, random_state=1)
model = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5)),
                      LogisticRegression(max_iter=1000))
model.fit(X_tr, y_tr)
print(classification_report(y_te, model.predict(X_te)))  # use this in your report/viva

joblib.dump(model.fit(df.text, df.label), MODEL_PATH)  # final model on all data
print("Saved model.pkl")
