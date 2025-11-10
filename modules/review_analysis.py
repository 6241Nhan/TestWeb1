# Can cai thu vien transformer de chay
# Buoc 1: Mo terminal cua Visual Studio 2022
# Buoc 1: Cai pip(Kiem tra xem pip da cai chua, neu cai roi thi thoi)
# Buoc 2: Cai transformer: ghi pip install transformers torch vao terminal của VS2022

from transformers import pipeline
# Dung pipeline phan tich cam xuc
review_analysis = pipeline("sentiment-analysis")
def analyze_review(review: str):
    result = review_analysis(review)[0]
    label = result['label']
    score = result['score']
    return f"{label} ({score:.2f})"
# Demo ----------------------------------
print(analyze_review("I love this product, it's umazing"))
print(analyze_review("This thing is shit"))
