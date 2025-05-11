import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud as wc
from datetime import datetime, timedelta, timezone

APIKEY = "a9b5797e-c445-4359-bd56-86b30652dfa0"

CACHE_ARTICLE_FILES = "cache/articles.csv"
CACHE_WORDCLOUD_TEXT = "cache/wordcloud_text.csv"

#1. Extract data from API's / web scraping / or a dataset. Save the data to a file in your cache folder.

def import_articles(section: str, max_pages: int = 5):
    all_articles = []

    st.text(f"Fetching headlines...")
    for page in range(1, max_pages + 1):

        header = {'api-key': APIKEY}
        params = {
            'order-by': 'newest',
            'section': section,
            'page-size': 200,
            'page': page,
            'type': 'article'
        }
        url = "https://content.guardianapis.com/search"
        response = requests.get(url, headers=header, params=params)
        response.raise_for_status()

        articles = response.json().get('response', {}).get('results', [])
        all_articles.extend(articles)

    article_df = pd.json_normalize(all_articles)
    article_df.to_csv(CACHE_ARTICLE_FILES, index=False, header=True)

    return article_df

def get_sections() -> list:
    url = "https://content.guardianapis.com/sections"
    headers = {'api-key': APIKEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    sections = [section['id'] for section in data['response']['results']]
    return sections

def filter_articles_by_weeks(df: pd.DataFrame, weeks: int) -> pd.DataFrame:
    df['webPublicationDate'] = pd.to_datetime(df['webPublicationDate'], utc=True)
    today = datetime.now(timezone.utc)
    start_date = today - timedelta(weeks=weeks)
    filtered_df = df[df['webPublicationDate'] >= start_date]
    return filtered_df

#2. Transform the data into a format that is useful for your dashboard. Save the data to a file in your cache folder.

def publication_freq(df: pd.DataFrame):
    df['webPublicationDate'] = pd.to_datetime(df['webPublicationDate'])
    df['date'] = df['webPublicationDate'].dt.date
    daily_counts = df.groupby('date').size()

    plot, ax = plt.subplots(figsize=(10, 5))
    ax.plot(daily_counts.index, daily_counts.values, marker='', linestyle='-', color='blue')
    ax.set_title("Article Publication Frequency Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Articles")
    ax.grid(True)

    return plot

def extract_and_clean_headlines(df: pd.DataFrame):
    headlines = df['webTitle'].dropna()
    cleaned_headlines = [headline.split('|')[0].strip() for headline in headlines]
    text = ' '.join(cleaned_headlines)
    text = text.replace("’",'').replace('‘','').replace(':','').replace('?','')
    with open(CACHE_WORDCLOUD_TEXT, 'w', encoding='utf-8') as file:
        file.write(text)

    return text

def create_wordcloud(text: str):
    
    wordcloud = wc(width=800, height=400, background_color='#0e1117', colormap='Set3', normalize_plurals=True).generate(text)

    plot, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')

    return plot

#3. Load the data into a pandas and interact with it using streamlit and charts, graphs or maps.

st.set_page_config(page_title="IST356", layout="wide")

if 'article_df' not in st.session_state:
    st.session_state.article_df = pd.DataFrame()
if 'section' not in st.session_state:
    st.session_state.section = None

col1, col2 = st.columns(2)

with col1:
    st.title("Guardian Headlines")
    st.subheader("Get a sense of the latest developments within certain topics of the news.")
    section = st.selectbox('Select a Topic:', get_sections())
    timeframe = st.slider('Select a Timeframe (weeks):', min_value=1, max_value=12)
    if section != st.session_state.section:
        st.session_state.section = section
        st.session_state.article_df = import_articles(section, max_pages=10)
    if not st.session_state.article_df.empty:
        filtered_article_df = filter_articles_by_weeks(st.session_state.article_df, timeframe)
        st.dataframe(filtered_article_df[['webPublicationDate', 'webTitle']])

with col2:
    st.pyplot(create_wordcloud(extract_and_clean_headlines(filtered_article_df)))
    st.pyplot(publication_freq(filtered_article_df))