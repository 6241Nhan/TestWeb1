import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from textblob import TextBlob

class HybridRecommender:
    def __init__(self, hotel_data, booking_data, review_data):
        self.hotels = pd.read_csv(hotel_data)
        self.bookings = pd.read_csv(booking_data)
        self.reviews = pd.read_csv(review_data)
        self.hotel_profiles = self._build_hotel_profiles()
        self.sentiment_scores = self._compute_sentiment_scores()

    def _build_hotel_profiles(self):
        # Combine hotel features into a single string
        self.hotels['features'] = self.hotels[['location', 'amenities', 'price_range']].fillna('').agg(' '.join, axis=1)
        tfidf = TfidfVectorizer()
        tfidf_matrix = tfidf.fit_transform(self.hotels['features'])
        return tfidf_matrix

    def _compute_sentiment_scores(self):
        sentiment = self.reviews.groupby('hotel_id')['review'].apply(lambda reviews: 
            sum(TextBlob(r).sentiment.polarity for r in reviews) / len(reviews))
        return sentiment.to_dict()

    def _get_user_profile(self, user_id):
        user_hotels = self.bookings[self.bookings['user_id'] == user_id]['hotel_id']
        return self.hotel_profiles[user_hotels.index]

    def recommend(self, user_id, top_n=5):
        user_profile = self._get_user_profile(user_id)
        if user_profile.shape[0] == 0:
            return self.hotels.sample(top_n)

        # Collaborative score: similarity to user's past bookings
        sim_scores = cosine_similarity(user_profile.mean(axis=0), self.hotel_profiles).flatten()

        # Sentiment score
        sentiment = self.hotels['hotel_id'].map(self.sentiment_scores).fillna(0).values

        # Final score: weighted sum
        final_score = 0.6 * sim_scores + 0.4 * sentiment
        top_indices = final_score.argsort()[::-1][:top_n]
        return self.hotels.iloc[top_indices][['hotel_id', 'name', 'location', 'price', 'rating']]

