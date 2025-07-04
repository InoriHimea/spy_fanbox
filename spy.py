import httpx
import json
from string import Template
import sqlite3
import os
from pathlib import Path

creator_id=""
#fee=500

url_1=Template("https://api.fanbox.cc/post.paginateCreator?creatorId=$creatorId&sort=newest")
url_2=Template("https://api.fanbox.cc/post.info?postId=$postId")

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.fanbox.cc",
    "Referer": "https://www.fanbox.cc/",
    "Cookie": ""
}

spy_data = []

def download_cover(client, url):
    print(f'下载封面数据: {url}')


def download_files(client, cur, files, arr, item_id, item_title):
    print(f'下载所有附件: {len(arr)}')
    
    for file in arr:
        id = file['id']
        name = file['name']
        ext = file['extension']
        size = file['size']
        url = file['url']
        print(f'当前的项目: [{id}]{name} -> {size}: {url}')

        path = os.path.join(creator_id, "[" + item_id + "]" + item_title, name + "." + ext)
        cur.execute('INSERT INTO files_info(id, name, extension, size, url, save_path) VALUES(?, ?, ?, ?, ?, ?)', (id, name, ext, size, url, path))

        files.append(id)

        download = os.path.join(os.getcwd(), path)
        if os.path.exists(download) is False:
            os.makedirs(Path(download).parent)

        request = client.build_request('GET', url)
        response = client.send(request)

        body = response.content
        print(f"大小: {size} -> {len(body)}")

        with open(download, 'wb') as file:
            file.write(body)


def download_images(cur, images, arr, item_id, item_title):
    print(f'下载所有图片: {len(arr)}')

    for file in arr:
        id = file['id']
        ext = file['extension']
        width = file['width']
        height = file['height']
        original_url = file['height']
        thumbnail_url = file['height']
        print(f'当前的项目: [{id}][{width}/{height}] -> {original_url}')

        path = os.path.join(creator_id, "[" + item_id + "]" + item_title, id + "." + ext)
        cur.execute('INSERT INTO files_info(id, extension, width, height, original_url, thumbnail_url, save_path) VALUES(?, ?, ?, ?, ?, ?)', (id, ext, width, height, original_url, thumbnail_url, path))

        images.append(id)

        download = os.path.join(os.getcwd(), path)
        if os.path.exists(download) is False:
            os.makedirs(Path(download).parent)

        request = client.build_request('GET', original_url)
        response = client.send(request)

        body = response.content

        with open(download, 'wb') as file:
            file.write(body)


if __name__ == '__main__':
    print('开始爬取fanbox站数据')

    conn = sqlite3.connect(creator_id + '.db')
    cur = conn.cursor()

    cur.execute('CREATE TABLE IF NOT EXISTS spy_info(' \
                                'id varchar(255) PRIMARY KEY not null,' \
                                'title varchar(255),' \
                                'fee int,' \
                                'published_date_time varchar(255),' \
                                'updated_date_time varchar(255),' \
                                'type varchar(30),' \
                                'cover_image_url varchar(500),' \
                                'content text,' \
                                'images text,' \
                                'files text' \
                ')')
    cur.execute('CREATE TABLE IF NOT EXISTS files_info(' \
                                'id varchar(255) PRIMARY KEY not null,' \
                                'name varchar(255),' \
                                'extension varchar(10),' \
                                'size bigint,' \
                                'url varchar(500),' \
                                'save_path varchar(500)' \
                ')')
    cur.execute('CREATE TABLE IF NOT EXISTS images_info(' \
                                'id varchar(255) PRIMARY KEY not null,' \
                                'extension varchar(10),' \
                                'width int,' \
                                'height int,' \
                                'original_url varchar(500),' \
                                'thumbnail_url varchar(500),' \
                                'save_path varchar(500)' \
                ')')

    client = httpx.Client(headers=headers)
    try:
        request = client.build_request('GET', url_1.substitute(creatorId=creator_id))
        response = client.send(request)

        body = response.content.decode('utf-8')
        #print(body)

        body_json = json.loads(body)
        page_data = body_json['body']
        page_size = len(page_data)
        print(f'page_size: {page_size}')

        for page in page_data:
            print(f'处理的页面地址信息: {page}')

            request = client.build_request('GET', page)
            response = client.send(request)

            body = response.content.decode('utf-8')
            #print(body)

            body_json = json.loads(body)
            item_data = body_json['body']
            item_size = len(item_data)
            print(f'item_size: {item_size}')

            for item in item_data:
                item_id = item['id']
                item_title = item['title']
                item_fee = item['feeRequired']
                item_publishedDatetime = item['publishedDatetime']
                item_updatedDatetime = item['updatedDatetime']

                print(f'处理的条目数据: {item_title}[{item_id}]-[{item_fee}]')
                print(f'处理的条目时间: {item_publishedDatetime} - {item_updatedDatetime}')

                res = cur.execute('SELECT count(id) from spy_info where id = ?', (item_id,))
                record = res.fetchone()
                if record[0] == 1:
                    print(f'当前内容已处理且入库，暂不重复处理: {item_title}[{item_id}]-[{item_fee}]')
                    continue 

                request = client.build_request('GET', url_2.substitute(postId=item_id))
                response = client.send(request)

                body = response.content.decode('utf-8')
                #print(body)

                body_json = json.loads(body)
                item_info = body_json['body']
                print(f'item信息: {item_info}')

                item_type = item_info['type']
                item_cover = item_info['coverImageUrl']
                item_attachments = item_info['body']
                print(f'资源类型: {item_type}')

                if item_attachments is None:
                    print('当前没有包含附件')
                    spy_data.append((item_id, item_title, item_fee, item_publishedDatetime, item_updatedDatetime, item_type, item_cover, "", "", ""))
                    continue
                
                content = item_attachments['text']
                print(f'资源正文: {content}')

                images = []
                files = []

                if item_type == 'file':
                    download_files(client, cur, files, item_attachments['files'], item_id, item_title)
                    conn.commit()
                elif item_type == 'image':
                    download_images(client, cur, images, item_attachments['images'], item_id, item_title)
                    conn.commit()
                else:
                    print('位置的类型，暂不处理')

                spy_data.append((item_id, item_title, item_fee, item_publishedDatetime, item_updatedDatetime, item_type, item_cover, content, json.dumps(images), json.dumps(files)))

            print('处理内容入库')
            cur.executemany('INSERT INTO spy_info(id, title, fee, published_date_time, updated_date_time, type, cover_image_url, content, images, files) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', spy_data)
            conn.commit()

        print('所有页已处理完毕')

    finally:
        client.close()
