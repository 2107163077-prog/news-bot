import os
import time
import requests
import feedparser
from urllib.parse import quote
from google import genai

# 環境変数の取得
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 1. ニュース（RSS）の収集
def fetch_news_titles():
    queries = ["薬学 研究 免疫 遺伝学", "製薬 経済 薬価 市場動向"]
    articles = []
    for q in queries:
        encoded_q = quote(q)
        url = f"https://news.google.com/rss/search?q={encoded_q}&hl=ja&gl=JP&ceid=JP:ja"
        
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:  # 各検索クエリ上位5件
            articles.append(f"- タイトル: {entry.title}\n  URL: {entry.link}")
            
    return "\n".join(articles)

# 2. AIによる要約生成
def generate_digest(news_data):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
以下の最新ニュース情報をもとに、モーニングニュースダイジェストを作成してください。

情報源:
{news_data}

出力フォーマットとルール:
1. 以下の4つのセクションに厳密に分けて出力してください。セクション間は `---SECTION_BREAK---` という文字列で区切ってください。

【セクション1】
ヘッダー（日付入りタイトルと挨拶、1〜2文）

【セクション2】
🔬 **薬学研究セクション**
- 3〜5件のトピック。各2〜3文。参考URLを明記。特に重要なものに「⭐ 注目」タグ。

【セクション3】
💼 **ビジネス・経済セクション**
- 3〜5件のトピック。各2〜3文。参考URLを明記。特に重要なものに「⭐ 注目」タグ。

【セクション4】
☀️ **今日のまとめ**（全体を1〜2文で締める）
"""
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text

# 3. Discordへ分割送信
def send_to_discord(section_text):
    payload = {"content": section_text.strip()}
    res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if res.status_code == 204:
        print("送信成功 (204)")
    else:
        print(f"送信失敗: {res.status_code}, {res.text}")

def main():
    print("ニュースを取得中...")
    news_data = fetch_news_titles()
    
    print("AIダイジェストを生成中...")
    digest_raw = generate_digest(news_data)
    
    # セクションごとに分割して順次送信
    sections = digest_raw.split("---SECTION_BREAK---")
    for section in sections:
        if section.strip():
            send_to_discord(section)
            time.sleep(1) # 連続送信によるレート制限を回避

if __name__ == "__main__":
    main()
