import requests
import json
import time
from urllib.parse import quote
import re
import os


print("Hello world")

import aiohttp
import asyncio
import os

async def download_file(url, local_filename=None, file_dict=None):
    if local_filename is None:
        local_filename = url.split('/')[-1]

    if file_dict:
        file_path = os.path.join(file_dict, local_filename)
    else:
        file_path = local_filename

    async def attempt_download(url, file_path):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                "Referer": "https://www.pixiv.net/en/"
            }
            async with aiohttp.ClientSession() as session:  # Use aiohttp session
                async with session.get(url, headers=headers) as r:
                    r.raise_for_status()
                    with open(file_path, 'wb') as f:
                        async for data in r.content.iter_chunks():  # Asynchronous iteration
                            f.write(data[0])  # Write each chunk
            print(f"Download complete for {local_filename}")
            return file_path

        except aiohttp.ClientError as e: # Correct error type
            print(f"Download failed for {local_filename}: {e}")
            return None

    downloaded_file_path = await attempt_download(url, file_path)  # Await the download attempt


    if downloaded_file_path is None and url.endswith(".jpg"):
        png_url = url.replace(".jpg", ".png")
        png_filename = local_filename.replace(".jpg", ".png")
        if file_dict:
            png_file_path = os.path.join(file_dict, png_filename)
        else:
            png_file_path = png_filename
        downloaded_file_path = await attempt_download(png_url, png_file_path) # Await second attempt

    return downloaded_file_path

# @title Current
global inside_data

def convert_to_lowercase_if_english(word):
    return re.sub(r'[a-zA-Z]+', lambda x: x.group().lower(), word)

def construct_pixiv_image_url(artwork):
    illust_id = artwork['id']
    create_date = artwork['createDate']
    year, month, day = create_date.split('T')[0].split('-')
    hour, minute, second = create_date.split('T')[1].split('+')[0].split(':')
    extension = artwork['url'].split('.')[-1]

    if artwork.get("aiType", 0) == 2:
        base_url = f"https://i.pximg.net/img-master/img/{year}/{month}/{day}/{hour}/{minute}/{second}/{illust_id}_p0_master1200"
    else:
        base_url = f"https://i.pximg.net/img-original/img/{year}/{month}/{day}/{hour}/{minute}/{second}/{illust_id}_p0"

    if extension.lower() in ("jpg", "jpeg", "png"):
        return f"{base_url}.{extension.lower()}"
    else:
        print(f"Warning: Unknown extension '{extension}' for artwork ID {illust_id}. Defaulting to jpg.")
        return f"{base_url}.jpg"

def get_pixiv_search_results(query, tags=None, max_pages=1, language="en", page=1, session_id=None):
    all_results = []
    encoded_query = quote(query)
    defined_tags_lower = [convert_to_lowercase_if_english(tag) for tag in tags] if tags else []

    session = requests.Session()
    cookies = {  # **UPDATE THESE COOKIES FROM YOUR BROWSER**
        #"dic_pixiv_uid": "dont' put",
        #"pixpsession2": "don't put",
        "PHPSESSID": session_id,
        #"__cf_bm": "don't put",
        #"a_type": "don't put",
        #"b_type": "don't put",
        #"c_type": "don't put",
        #"cf_clearance": "don't put",
        #"default_service_is_touch": "don't put",
        #"device_token": "don't put",
        #"first_visit_datetime_pc": "don't put",
        #"p_ab_d_id": "don't put",
        #"p_ab_id": "don't put",
        #"p_ab_id_2": "don't put",
        #"privacy_policy_agreement": "don't put",
        #"privacy_policy_notification": "don't put",
        #"yuid_b": "don't put"
    }
    session.cookies.update(cookies)

    while True:
        s_mode = "s_tag_full" if page > 10 else "s_tag"
        url = f"https://www.pixiv.net/ajax/search/artworks/{encoded_query}"
        params = {
            "word": query,
            "order": "date_d",
            "mode": "all",
            "p": page,
            "s_mode": s_mode,
            "type": "all",
            "lang": language,
            "csw": 0,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "Referer": f"https://www.pixiv.net/en/tags/{encoded_query}/artworks?p={page}",
            #"x-user-id": "don't put",
        }

        try:
            response = session.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            inside_data = data

            if data["error"]:
                print(f"Pixiv API returned an error: {data.get('message', 'Unknown error')}")
                return None

            artworks_data = data["body"].get("illustManga", {}).get("data", [])
            if not artworks_data:
                print(f"No artwork data found on page {page}.")
                break

            for artwork in artworks_data:
                artwork_tags = [convert_to_lowercase_if_english(tag.lower()) for tag in artwork.get("tags", [])]
                #print(artwork_tags)

                if defined_tags_lower and not all(tag in artwork_tags for tag in defined_tags_lower):
                    continue

                image_url = construct_pixiv_image_url(artwork)
                all_results.append({
                    "id": artwork["id"],
                    "title": artwork["title"],
                    "original_url": image_url,
                    "tags": artwork.get("tags", []),
                })

            print(f"Processed page {page}")

            # Check if there are more pages
            total_results = data["body"]["illustManga"]["total"]
            results_per_page = len(artworks_data)
            if page * results_per_page >= total_results:
                print("Reached the last page of results.")
                break

            if max_pages is not None and page >= max_pages:
                break

            page += 1
            time.sleep(2)

        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error: {e}")
            return None

    return all_results
"""
# Example usage:
query = "オリジナル10000users入り"
tags_to_filter = []
max_pages = 3
starting_page = 1
language = "en"

search_data = get_pixiv_search_results(query, tags=tags_to_filter, max_pages=max_pages, language=language, page=starting_page)

if search_data:
    print(f"Retrieved {len(search_data)} results matching the tags.")
    for result in search_data:
        print("ID:", result["id"])
        print("Title:", result["title"])
        print("Original URL:", result["original_url"])
        print("-" * 20)
else:
    print("Could not retrieve search results.")"""