import feedgenerator
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

def generate_rss():
    # URL of the news website
    url = "https://citinewsroom.com/news/"
    
    # Fetch the webpage
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Create the RSS feed
    feed = feedgenerator.Rss201rev2Feed(
        title="Citinewsroom News Feed",
        link=url,
        description="Latest news from Citinewsroom",
        language="en"
    )
    
    # Find and add news items to the feed
    news_items = soup.find_all(['article', 'div'], class_=['jeg_post', 'jeg_pl_lg_2', 'jeg_pl_md_box', 'jeg_pl_sm', 'jeg_pl_xs_2', 'jeg_pl_xs_4'])
    
    for item in news_items:
        title = item.find(['h3', 'h2'], class_='jeg_post_title').text.strip()
        link = item.find('a')['href']
        
        # Try to find description
        description = ""
        desc_elem = item.find('div', class_='jeg_post_excerpt')
        if desc_elem:
            description = desc_elem.text.strip()
        
        # Try to find image
        image_url = ""
        img_elem = item.find('img')
        if img_elem and 'src' in img_elem.attrs:
            image_url = img_elem['src']
        
        # Use current time as publication date
        pub_date = datetime.now(pytz.UTC)
        
        feed.add_item(
            title=title,
            link=link,
            description=description,
            pubdate=pub_date,
            unique_id=link
        )
        
        # Add image to the item's description if available
        if image_url:
            feed.items[-1]['description'] += f'<br><img src="{image_url}" alt="{title}">'
    
    # Generate the RSS feed
    with open('citinewsroom_feed.xml', 'w', encoding='utf-8') as f:
        feed.write(f, 'utf-8')

if __name__ == "__main__":
    generate_rss()
    print("RSS feed generated: citinewsroom_feed.xml")
