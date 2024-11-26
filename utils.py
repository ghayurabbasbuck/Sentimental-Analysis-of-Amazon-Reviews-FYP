import os
import json
import pandas as pd
from bs4 import BeautifulSoup
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from collections import defaultdict
import nltk
nltk.download('vader_lexicon')

def fetch_product_details(html_content):
    productPageHtml = BeautifulSoup(html_content, 'html.parser')

    product_title_tag = productPageHtml.find('h1', class_='a-size-large')
    product_title = product_title_tag.text.strip() if product_title_tag else "N/A"

    img_div = productPageHtml.find('div', class_='a-text-center a-spacing-top-micro a-fixed-left-grid-col product-image a-col-left')
    img_tag = img_div.find('img') if img_div else None
    img_url = img_tag['src'] if img_tag else "N/A"

    reviews = []
    review_sections = productPageHtml.find_all('div', {'class': 'a-section review aok-relative'})

    for section in review_sections:
        review_title_tag = section.find('a', {'data-hook': 'review-title'})
        review_title = review_title_tag.text.strip() if review_title_tag else "N/A"

        reviewer_name_tag = section.find('span', class_='a-profile-name')
        reviewer_name = reviewer_name_tag.text.strip() if reviewer_name_tag else "N/A"

        review_date_tag = section.find('span', {'data-hook': 'review-date'})
        review_date = review_date_tag.text.strip() if review_date_tag else "N/A"

        review_text_tag = section.find('span', {'data-hook': 'review-body'})
        review_text = review_text_tag.text.strip() if review_text_tag else "N/A"

        review_data = {
            'review_title': review_title,
            'reviewer_name': reviewer_name,
            'review_date': review_date,
            'review_text': review_text
        }

        reviews.append(review_data)

    return {
        "product_title": product_title,
        "img_url": img_url,
        "reviews": reviews
    }

def process_html_files(directory_path, output_file_path):
    if os.path.exists(output_file_path):
        os.remove(output_file_path)

    all_products_data = []

    for filename in os.listdir(directory_path):
        if filename.endswith('.html'):
            file_path = os.path.join(directory_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
                product_details = fetch_product_details(html_content)

                product_exists = False
                for existing_product in all_products_data:
                    if existing_product['product_title'] == product_details['product_title']:
                        existing_product['reviews'].extend(product_details['reviews'])
                        product_exists = True
                        break

                if not product_exists:
                    all_products_data.append(product_details)

    with open(output_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(all_products_data, json_file, ensure_ascii=False, indent=4)

def json_to_reviews_dataframe(json_file_path):
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"The file {json_file_path} does not exist.")

    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        all_products_data = json.load(json_file)

    reviews_data = []

    for product in all_products_data:
        product_title = product.get('product_title')
        img_url = product.get('img_url')

        for review in product.get('reviews', []):
            review_data = {
                'product_title': product_title,
                'img_url': img_url,
                'review_title': review.get('review_title'),
                'reviewer_name': review.get('reviewer_name'),
                'review_date': review.get('review_date'),
                'review_text': review.get('review_text')
            }
            reviews_data.append(review_data)

    reviews_df = pd.DataFrame(reviews_data)

    return reviews_df


def analyze_sentiment_and_extract_words(reviews_df):
    sid = SentimentIntensityAnalyzer()

    positive_words = defaultdict(int)
    negative_words = defaultdict(int)
    neutral_words = defaultdict(int)

    total_reviews = len(reviews_df)
    num_positive = 0
    num_negative = 0
    num_neutral = 0

    for review_text in reviews_df['review_text']:
        sentiment_scores = sid.polarity_scores(review_text)

        if sentiment_scores['compound'] > 0:
            num_positive += 1
            for word in review_text.split():
                if sid.polarity_scores(word)['compound'] > 0:
                    positive_words[word] += 1
        elif sentiment_scores['compound'] < 0:
            num_negative += 1
            for word in review_text.split():
                if sid.polarity_scores(word)['compound'] < 0:
                    negative_words[word] += 1
        else:
            num_neutral += 1
            for word in review_text.split():
                if sid.polarity_scores(word)['compound'] == 0:
                    neutral_words[word] += 1

    positive_percent = (num_positive / total_reviews) * 100
    negative_percent = (num_negative / total_reviews) * 100
    neutral_percent = (num_neutral / total_reviews) * 100

    positive_words = dict(sorted(positive_words.items(), key=lambda item: item[1], reverse=True))
    negative_words = dict(sorted(negative_words.items(), key=lambda item: item[1], reverse=True))
    neutral_words = dict(sorted(neutral_words.items(), key=lambda item: item[1], reverse=True))

    positive_words_str = ', '.join(positive_words.keys())
    negative_words_str = ', '.join(negative_words.keys())
    neutral_words_str = ', '.join(neutral_words.keys())

    return positive_percent, negative_percent, neutral_percent, positive_words_str, negative_words_str, neutral_words_str
