### crawling 모듈
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from fake_useragent import UserAgent
from requests.api import head
ua = UserAgent()


from typing import Optional, Dict

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Safari/537.36"
)

PRODUCT_PAGE = "https://www.coupang.com/vp/products/7225189423"
XHR_ENDPOINT = "https://www.coupang.com/vm/v5/products/8250433942/vendor-items/90776061353"


def build_headers(
    mode: str,                     # "html" 또는 "json"
    ua: Optional[str] = None,      # User-Agent
    referer: Optional[str] = None, # Referer
    cookie: Optional[str] = None,  # 쿠키 문자열 (필요 시)
    extra: Optional[Dict[str, str]] = None,  # 필요하면 추가로 덮어쓰기
) -> Dict[str, str]:
    """
    목적에 따라 공통/차등 헤더를 구성한다.
    - mode="html": 문서(HTML) 수신
    - mode="json": XHR/Fetch(JSON) 수신
    """
    ua = ua or DEFAULT_UA

    # 공통 헤더 (둘 다에 들어감)
    headers = {
        "user-agent": ua,
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    if referer:
        headers["referer"] = referer
    if cookie:
        headers["cookie"] = cookie

    # 모드별 차등 헤더
    if mode == "html":
        headers.update({
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        # requests가 압축 인코딩은 자동 처리하지만 명시하고 싶다면:
        # headers["accept-encoding"] = "gzip, deflate, br, zstd"

    elif mode == "json":
        headers.update({
            "accept": "application/json, text/plain, */*",
        })
        # JSON XHR일 때도 필요시 인코딩 명시 가능
        # headers["accept-encoding"] = "gzip, deflate, br, zstd"
    else:
        raise ValueError("mode는 'html' 또는 'json'이어야 합니다.")

    # 추가 헤더 덮어쓰기
    if extra:
        headers.update(extra)

    return headers

def crawl_data(url, headers, params=None):
    """
    주어진 URL에서 데이터를 크롤링하는 함수입니다.
    
    Args:
        url (str): 크롤링할 웹 페이지의 URL
        headers (dict): HTTP 요청 헤더
        params (dict, optional): 추가적인 요청 파라미터. 기본값은 None.
        
    Returns:
        BeautifulSoup: 크롤링한 웹 페이지의 BeautifulSoup 객체
    """
    try:
        print("Crawling module loaded successfully.")   
        response = requests.get(url, headers=headers, params=params)
        print(response.status_code)
        print(response.url)
        print(response.text)
        with open("DS_project/response.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        # response.raise_for_status()  # HTTP 오류가 발생하면 예외를 발생시킴
        # soup = BeautifulSoup(response.text, 'html.parser')
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error during requests to {url} : {str(e)}")
        return None



# url = "https://www.coupang.com/vp/products/7225189423" => html받기

# headers = {
# "accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
# "accept-encoding" : "gzip, deflate, br, zstd",
# "accept-language" : "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
# "cache-control" : "max-age=0",
# "cookie" : "PCID=17463420738828750192085; MARKETID=17463420738828750192085; _fbp=fb.1.1746342076379.322486828382719822; delivery_toggle=false; x-coupang-target-market=KR; x-coupang-accept-language=ko-KR; bm_ss=ab8e18ef4e; bm_so=7E3D0B0CE5FEA6784F14F66138D02A796EE74F8B2BB3ACF33500ECA4D76E2493~YAAQDNojF1RLYKeZAQAAvCEl0gXYHGd4iNbddA0vAfSOSFms9ItslNC3Iv8//9nAODTWPlJAq2nA0z1lOhMDh+xjNC94ZZDCaeOfN9YgakiCspKewVrp7fBmVIYTmz1F8i6kpktXgs2ubqL+5L7s/4nmTU5IV7cJL/LwUPlszKEMrDZ86ULT+Y3mas8gfXNO8ZDLzlBBfkKzXLRsY84r/Ml1stZ5lxOOXB0gym32MMTfVLsUUPmV7wytFmHuYv99heULhZCUhN8/ypRCLIu7WoByTo1GkDcEffLCtL6beYEMtZ56C+xvEdF2PG9GM8ptcY34IDFak9CJ0lvoHz6+ffsRQL0vYbmM93MtjlYQh/ryM5qo5GoNxUM3LrIqIfkCZGoDV/NrZ7QJI62s06Z6cvBciwZn98gsIowT7m+d2OxjLjRCVJmTWs1ssj0jTY9/2/KpqLU02Uscwd1Ld96h; bm_sz=6C9BC1413D011E42DEDBB1F670A81AD4~YAAQDNojF1VLYKeZAQAAvCEl0h3NjzhBxzxkvFyHSiF0KbXxK+LWqBinSfMqvGki2D3JvtkZySuDlbWOeZ2X7r8r3795PW62T9PDRh+xgfHGFqGkpyoAPMi2YqxYkRMCjqMpX7zoqS+PeVAV0B4vdRmaCl870+AE4zsf9hFM3p9TzXu1lL0ddfdSmJCJGXS1SUK8zoh5e0LOUVZmuIqEF3gE6juYzUuH5XCjBVoH5J5dpvSp/5pE3lekF5MbuHl8Fl/ndAuQg8W4i29Iv2bGaoN+Ayq/t8AHeR789bnfrU4SQu5MUOJZXMU+iHFq3kLNQWw4bLHFe7jLGntH8KUpUUFump9kW0yas0hxnsigYX6vnyyowepu4w==~3228995~3421761; ak_bmsc=CE7E1B77CEFC8A8D51D1D6A761D0C72F~000000000000000000000000000000~YAAQDNojF2JOYKeZAQAAVCUl0h1zWJr3QxvnGO3nojqagJIE43RjB8gHkF95i2zV66Zyg17KqitZjyt4e18veU6dGebuO40c9kGdVqQvx2wXx5ahZzpxnCqhle+/WwDFTzyMd5c+ROoadrvmmwXL3fMIdLu88msZT8QbzIg3uHVH8vxDX5YC0RO88K/p2Y+pEPLwaW/lvX7UGWUabGhMT9K14PVS4ts4Co/lAJGb+q3fxaW/2ppGeoIaadhTXuXgg7JCy9aT5jmGPIAY33D5VqGjjlFyBl/BE6v0SjAho6OpmgoGsi6aEZJDKwrEmvg7gBXX+VExty8rtIKn0R7zJIDEVk4aaLUesF4xDa64Dd0+wH9FPM6pHe4M5hXAG5P3unJaYP7CZ50SQjU8XpMwkBzwP+6K6XSbc95SqrqV6uKErf91AaIcwWuiusirL8ozMJARcFgOSVxhrfJf01ep; sid=917ba3097bf140eea38ef600e15484476998aff3; bm_lso=7E3D0B0CE5FEA6784F14F66138D02A796EE74F8B2BB3ACF33500ECA4D76E2493~YAAQDNojF1RLYKeZAQAAvCEl0gXYHGd4iNbddA0vAfSOSFms9ItslNC3Iv8//9nAODTWPlJAq2nA0z1lOhMDh+xjNC94ZZDCaeOfN9YgakiCspKewVrp7fBmVIYTmz1F8i6kpktXgs2ubqL+5L7s/4nmTU5IV7cJL/LwUPlszKEMrDZ86ULT+Y3mas8gfXNO8ZDLzlBBfkKzXLRsY84r/Ml1stZ5lxOOXB0gym32MMTfVLsUUPmV7wytFmHuYv99heULhZCUhN8/ypRCLIu7WoByTo1GkDcEffLCtL6beYEMtZ56C+xvEdF2PG9GM8ptcY34IDFak9CJ0lvoHz6+ffsRQL0vYbmM93MtjlYQh/ryM5qo5GoNxUM3LrIqIfkCZGoDV/NrZ7QJI62s06Z6cvBciwZn98gsIowT7m+d2OxjLjRCVJmTWs1ssj0jTY9/2/KpqLU02Uscwd1Ld96h^1760167275244; _abck=AA7EE0CF901C0D2CC04569436942CDFA~0~YAAQFdojF7RYdJyZAQAA+D8l0g5qPygb9akYUrf3Vk4v7qBIFL+UbB6OFY9BvZvSx85x9SyJuCPGH/dqRRFG574VYcB2R9F9p4pRG9W5S6A3YQpchTOARh/LA0YBD/UF15J5ty+RB5mi7ZNylmW0oUDqMhJkWKo2iNWZaoYVYLT1tJ4ev2nvjZldew6eOZfpS2gPgcyWUI9bbQ8f1C8wi2UlOI+/NZApep0HkCA4+KH3Eq2BGF8aWs6FYussC/Lqzhelt5Qq8mJLoU8ocizXrI4HAWb+kqc/XkQZRCQM2EhF0BmRxmTS+I6HSJ8WID3qImbXXGrKVoR27SaCMnbolp5lH6qRH10RrQgGfdf0lxOfzTnvszZnJ00/Qm8ix30BjTHmdC+ahd0GNyVKueGyqnWiNf7uu+s2pMtmDqh7grEYHNv7kqnfUUfsDaWSDlfLaE1TDtMD7lpy+3DiS9TrEsZzyMqR4MaSx/PZlpoS3h+JwtpD8HJ3oEkhlaaPjTz3FQ061CeBMWSehCCvY8x9R02tQmyY0UodjfO+9+rAkaJDQv0sYrmoGYZZL6Pzew9NHe9/7obcg8OLUwNHxgJhHK13hHFC~-1~-1~1760170873~AAQAAAAE%2f%2f%2f%2f%2fwaORoli8mMAWwINvXuoH%2fVE4Cq0OlDl2iZYW9skmEKEU3Bs%2fYmBGdJp1ft2LTWOFr3liLEYhXHEAzQdxxDDW5ENizQLSebPGlnS~-1; cto_bundle=Ch0-gl9EbHJGNDNscHB2aDJUT1A3JTJGQVk5Qm42cEdDUSUyRiUyRkNCd0d5R3RMc254dUdQbW1FRDhzNGxEM21qUnAlMkJTVmNIM3lFZXpMWnlWS2xSa08zQWVKMEdBbHlhcCUyQnRzSVB0RjJ5TjR0THRENThidjlqb2NrREhRT2F5WGglMkY1cUFIbmpncUFRNXYlMkYlMkJXSTNWRG13RDFFR1FITyUyRnclM0QlM0Q; bm_s=YAAQB9ojFzG/BKOZAQAAoEsl0gTIrE7dwKG9mkWTPLrZEl8eOhMKT3Ht/9gGZXUoKMdjCSiMgt0Egl/LqxzGK/1niiMHS1T9KNgi6ushx2Whkqij2+CGNnARucs/KA/Rw6CNCLKJ2+CmtwpwVeqEkoU87e/JOhw72g1DWqi9OJsYWozx0LOA3dxpUdr0f7ku4JA0zJ77Ub6CHRg1MLUeizKEf3g/4qlKhgZKMSsnYsV74LOWmY0HyRn3V1EYbgRFYi2Bn0H/5Yv36hoqLYeZynN+k+6QG1PCrySJ+rC2ivUWHfh/ya/CJ7v+XC61+qeFAeczFrWnS4rhfLuFKrcMW/fizkLsqIKhfLpalDXM6oRAzh1ZKHK76H4DHkJ69+pW6UCIETd8gEABp5uCnM13DYEPX5GXGtMdl+U/J6E2zAneGCQwNpIe/SEn1/smsZ8Rfg3HlENaL1+f+Sw4EcO9btFLdQ4JCOK27Rx/fciyYYoDTc2QLQ8g5GAUxrjZWeRAS7Fb/Du2EFhWblKTt0QEXsS3PfPoSpXH8DWtXXhqPc6rMc/dP7YOZoNnwDrCS987Ybw5clA=; bm_sv=36D3CAF1861ADE7576FEA7AAA8DB5911~YAAQFtojFwuX5p+ZAQAA11Ul0h0ewb2908q412ns3+ePun9M2CzvIODAGz2IGrBOiNfO27AL8DdKZoAwbZJNOpBmQ7/c8pgNJn9C321hSVkmgvWzDW51/xv2dFTdaDmW+0Z82y30pWm4U40SzY0biTIJdunGtTMzS+cI4PnARBXtoTm+7HIwBx3oxtkmdmqhO0B5VJof9HaKEz6bEEO6vQWW4UFBUcyFERqTKvQ2lZswG9Hy9rQ5zPg0ubKLkURWpA==~1",
# "dnt" : "1",
# "priority" : "u=0, i",
# "referer": "https://www.coupang.com/?src=1042016&spec=10304903&addtag=900&ctag=HOME&lptag=%EC%BF%A0%ED%8C%A1&itime=20251001153406&pageType=HOME&pageValue=HOME&wPcid=17463420738828750192085&wRef=www.google.com&wTime=20251001153406&redirect=landing&gclid=CjwKCAjw_-3GBhAYEiwAjh9fUH9UhT_S4_1NIqQcJfCOlTn9coVhLBQK3kuBAJUs1je7mGKi5MgJ4hoCru8QAvD_BwE&mcid=76c4193df8d1484eb2050cf1429eda6c&campaignid=8704277940&adgroupid=86483039646&network=g",
# "sec-ch-ua" : '"Chromium";v="141", "Not?A_Brand";v="8"',
# "sec-ch-ua-mobile" : "?0",
# "sec-ch-ua-platform" : "macOS",
# "sec-fetch-dest" : "document",
# "sec-fetch-mode" : "navigate",
# "sec-fetch-site" : "same-origin",
# "sec-fetch-user" : "?1",
# "upgrade-insecure-requests" : "1",
# "user-agent" : str(ua.random)
# }

# params = {
#     "itemId" : "23751564869",
# "vendorItemId" : "90776061353",
# "from" : "home_C2",
# "traid" : "home_C2",
# "trcid" : "4750066"
# }


url = 'https://www.coupang.com/next-api/products/quantity-info'#=> json 받기
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "cookie": "PCID=17463420738828750192085; MARKETID=17463420738828750192085; _fbp=fb.1.1746342076379.322486828382719822; delivery_toggle=false; x-coupang-target-market=KR; x-coupang-accept-language=ko-KR; bm_ss=ab8e18ef4e; ak_bmsc=CE7E1B77CEFC8A8D51D1D6A761D0C72F~000000000000000000000000000000~YAAQDNojF2JOYKeZAQAAVCUl0h1zWJr3QxvnGO3nojqagJIE43RjB8gHkF95i2zV66Zyg17KqitZjyt4e18veU6dGebuO40c9kGdVqQvx2wXx5ahZzpxnCqhle+/WwDFTzyMd5c+ROoadrvmmwXL3fMIdLu88msZT8QbzIg3uHVH8vxDX5YC0RO88K/p2Y+pEPLwaW/lvX7UGWUabGhMT9K14PVS4ts4Co/lAJGb+q3fxaW/2ppGeoIaadhTXuXgg7JCy9aT5jmGPIAY33D5VqGjjlFyBl/BE6v0SjAho6OpmgoGsi6aEZJDKwrEmvg7gBXX+VExty8rtIKn0R7zJIDEVk4aaLUesF4xDa64Dd0+wH9FPM6pHe4M5hXAG5P3unJaYP7CZ50SQjU8XpMwkBzwP+6K6XSbc95SqrqV6uKErf91AaIcwWuiusirL8ozMJARcFgOSVxhrfJf01ep; sid=917ba3097bf140eea38ef600e15484476998aff3; bm_lso=7E3D0B0CE5FEA6784F14F66138D02A796EE74F8B2BB3ACF33500ECA4D76E2493~YAAQDNojF1RLYKeZAQAAvCEl0gXYHGd4iNbddA0vAfSOSFms9ItslNC3Iv8//9nAODTWPlJAq2nA0z1lOhMDh+xjNC94ZZDCaeOfN9YgakiCspKewVrp7fBmVIYTmz1F8i6kpktXgs2ubqL+5L7s/4nmTU5IV7cJL/LwUPlszKEMrDZ86ULT+Y3mas8gfXNO8ZDLzlBBfkKzXLRsY84r/Ml1stZ5lxOOXB0gym32MMTfVLsUUPmV7wytFmHuYv99heULhZCUhN8/ypRCLIu7WoByTo1GkDcEffLCtL6beYEMtZ56C+xvEdF2PG9GM8ptcY34IDFak9CJ0lvoHz6+ffsRQL0vYbmM93MtjlYQh/ryM5qo5GoNxUM3LrIqIfkCZGoDV/NrZ7QJI62s06Z6cvBciwZn98gsIowT7m+d2OxjLjRCVJmTWs1ssj0jTY9/2/KpqLU02Uscwd1Ld96h^1760167275244; _abck=AA7EE0CF901C0D2CC04569436942CDFA~0~YAAQFdojF7RYdJyZAQAA+D8l0g5qPygb9akYUrf3Vk4v7qBIFL+UbB6OFY9BvZvSx85x9SyJuCPGH/dqRRFG574VYcB2R9F9p4pRG9W5S6A3YQpchTOARh/LA0YBD/UF15J5ty+RB5mi7ZNylmW0oUDqMhJkWKo2iNWZaoYVYLT1tJ4ev2nvjZldew6eOZfpS2gPgcyWUI9bbQ8f1C8wi2UlOI+/NZApep0HkCA4+KH3Eq2BGF8aWs6FYussC/Lqzhelt5Qq8mJLoU8ocizXrI4HAWb+kqc/XkQZRCQM2EhF0BmRxmTS+I6HSJ8WID3qImbXXGrKVoR27SaCMnbolp5lH6qRH10RrQgGfdf0lxOfzTnvszZnJ00/Qm8ix30BjTHmdC+ahd0GNyVKueGyqnWiNf7uu+s2pMtmDqh7grEYHNv7kqnfUUfsDaWSDlfLaE1TDtMD7lpy+3DiS9TrEsZzyMqR4MaSx/PZlpoS3h+JwtpD8HJ3oEkhlaaPjTz3FQ061CeBMWSehCCvY8x9R02tQmyY0UodjfO+9+rAkaJDQv0sYrmoGYZZL6Pzew9NHe9/7obcg8OLUwNHxgJhHK13hHFC~-1~-1~1760170873~AAQAAAAE/////waORoli8mMAWwINvXuoH/VE4Cq0OlDl2iZYW9skmEKEU3Bs/YmBGdJp1ft2LTWOFr3liLEYhXHEAzQdxxDDW5ENizQLSebPGlnS~-1; cto_bundle=Ch0-gl9EbHJGNDNscHB2aDJUT1A3JTJGQVk5Qm42cEdDUSUyRiUyRkNCd0d5R3RMc254dUdQbW1FRDhzNGxEM21qUnAlMkJTVmNIM3lFZXpMWnlWS2xSa08zQWVKMEdBbHlhcCUyQnRzSVB0RjJ5TjR0THRENThidjlqb2NrREhRT2F5WGglMkY1cUFIbmpncUFRNXYlMkYlMkJXSTNWRG13RDFFR1FITyUyRnclM0QlM0Q; bm_s=YAAQNbxBF0dqr+GZAQAATzom0gT55N+GISM0NzM/VtOy/e+DY6hoUZVuhNzv9gAZsqY/kCr1we2B7NBSO9sq2xGfUS8ernGjKtqPMpyL6SENwfZtcez2MfkOTfG6OGhv4HFv7xRLYiFRBuGOWZnsUuSVmDXLp3HOE9t+RnU4FMdBKKfiu8EakK62SgpdbkIRV/m7l3/mhPsBiMBLodogmdzael0uuUBItZ+EBUOSFV+DgJiWs/qoJVda3CemZUDu8C3ICvGL4zcrUn7HsIOT8LwIWvzykUePLIAKGiinIhLOfu1mOKuwJo6o8XcFNFJFl5E0LGTKUBgRRJiNQGHBifWbV7HFqmv+Jm1D7f8xQBRucVRL63NrMhdrhl95B6+GoJzg6Syo78Z0GEdJn29DTrLCcjCmf49rROxVHVb5rZBaHVogeTD9jIobQEfGS4oMZ7UkyKItVHZ/nCvlab5fHSMxGKSSk4NR+twVRQR27WOKyHXHvvJd2yyp60bXkUZ2vm1nJxI529Aep7ukCeX3BsY6zg6NIghQ+EncfSjPK9zYtPFe1GiERtXaZN/cKZmlxlWh8UI=; bm_so=6E18EF7644F2A8200F8C6FFA55022026076CAC441132F6BDB563B7467334AA6B~YAAQNbxBF0hqr+GZAQAATzom0gUyaaAE9wC9EpQRPEiXm5CNzCeds88d9K8heP8u80jAe3eguFlFTr5bMufhmMQESA9WLkOf+rIlmp/soEG6zrXZkPcUrv2+oSFQj9hDEO0a/IE+spY/lL0fUI6mnYK+FQavPu+ZolzMnHre+YRCqa4ibln7Y5siJ6XlTMyDB0SfIxA54S6s2srVFfuXqSL4ih/H0ROzA0Oe51iFBgYpFDaFELdQgf9Ct2oFKmGW8u+Tm9/0ZdSRHfrYSGagmeYE5P9KugssYynISlZ4X3ahJDhIY3135td5vLRMQsZ9B8LMOSFHG2cp4mpBakRc5r6f0Nyc1fL2HOhnpcOqJ7PWOJVwEDSSmPRBweJikXlvx1jJMQ4+kU2ZYLvPYHXzs6kSXKnu7gZDUSB1an9bKRtuT3f/HPJIjMXFFoIiWn5ztMoqtTyACH7KaGBpSP6Y; bm_sv=36D3CAF1861ADE7576FEA7AAA8DB5911~YAAQNbxBF0lqr+GZAQAATzom0h3P6IWxrxznEGvbdIpXZ9i22b1Ro3yUS7zr6UwiCCQytg/uY2G+i+NqiAP+SqeQQ+0rfvzYrew7x3IRRFQdm2sO034lhmHV4XJtckHLEGK6yZHZZk8GSM0JwhC55NESzzsDOYs2PJ1tZl17/CfTlf2HBfiovm1OZhuwNFbYtPjRPst9IHGGGZMUExox0qR7GDZev7L2jKF+D71FAa7jshYok9npBejCX92t5j//0C8=~1; bm_sz=6C9BC1413D011E42DEDBB1F670A81AD4~YAAQNbxBF0pqr+GZAQAATzom0h2RLR42M9GAYaHmpV5l8GFcfQIgOvLIdwyclDtH18xpn4lZRN4MTRnUb3cjCdPuTdzPwBGNA3GhNWtJ+CbNrqw/JbTq9WyglPC6AxkR6LXrQgpxxkwRXV56wlwAm/2QlFn8Jchj2FPeb3dxlI3gyRER0jgg1Jgj+UnHQjb/OaLwAFB4GVs10EXqMlwrfi6QAkXNfyNfJkDY0hKyUdZxp4dfKov4yC2XMOPtiBl4QtG3uZOGcl1CJgGVcscnyluzDyaxYKLhqI6i4mkYmZVrONoi4x+weoV55uFLH7pqv+Zvd9Mj2AqlC3WTDCZEtFW7ze68Wf64e+GSZG4sAyJUCrx4J/VYUHolAqRO7JMxued+VFL9xwO8eqObmP83nCc=~3228995~3421761",
    "dnt": "1",
    "priority": "u=1, i",
    "referer": "https://www.coupang.com/vp/products/7225189423?itemId=23751564869&vendorItemId=90776061353&from=home_C2&traid=home_C2&trcid=4750066",
    "sec-ch-ua": "\"Chromium\";v=\"141\", \"Not?A_Brand\";v=\"8\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
}
params = {
    "productId" : "8250433942",
    "vendorItemId" : "90776061353",
    "deliveryToggle" : "false",
    "landingItemId" : "23751564869",
    "landingProductId" : "8250433942",
    "landingVendorItemId" : "90776061353"
}    


url = "https://www.coupang.com/next-api/review"


print("Starting to crawl data...")
crawl_data = crawl_data(url, headers, params)
print(crawl_data.prettify()[:1000])  # 크롤링한 데이터의 일부를 출력하여 확인
