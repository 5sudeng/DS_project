프로젝트 커밋 히스토리
프로젝트 시작부터 현재까지의 모든 커밋에 대한 상세 로그입니다.

1. first commit
Date: 2025-10-07
Author: 5sudeng
Hash: 69beab8
Changes
README.md | 1 +
 1 file changed, 1 insertion(+)
2. Add initial implementation of web scraping modules for Coupang products
Date: 2025-10-11
Author: ssunggun2
Hash: 8ce7628
Changes
"\breview.py" |  88 +++++++++++++++++++++++++++++++
 fetch_html.py |  52 +++++++++++++++++++
 inquiries.py  |  83 ++++++++++++++++++++++++++++++
 quantity.py   |  79 ++++++++++++++++++++++++++++
 test.py       | 163 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 5 files changed, 465 insertions(+)
3. rename
Date: 2025-10-13
Author: 5sudeng
Hash: 6c58b99
Changes
review.py | 88 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 88 insertions(+)
4. add pathlib
Date: 2025-10-21
Author: 5sudeng
Hash: 6fd2c80
Changes
quantity.py | 10 ++++++++--
 1 file changed, 8 insertions(+), 2 deletions(-)
5. crawl urls
Date: 2025-10-22
Author: 5sudeng
Hash: b9eae08
Changes
crawl_category_urls.py | 205 +++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 205 insertions(+)
6. products csv
Date: 2025-10-22
Author: 5sudeng
Hash: e1e1397
Changes
make_products_csv.py | 278 +++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 278 insertions(+)
7. csv
Date: 2025-10-22
Author: 5sudeng
Hash: a0cf1b5
Changes
products.csv | 1025 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 1025 insertions(+)
8. git ignore
Date: 2025-10-22
Author: 5sudeng
Hash: 6c14221
Changes
.gitignore | 2 ++
 1 file changed, 2 insertions(+)
9. codes update: crawling
Date: 2025-10-22
Author: 5sudeng
Hash: c073798
Changes
fetch_html.py | 417 +++++++++++++++++++++++++++++++++++++++++++++++++++++-----
 inquiries.py  | 215 ++++++++++++++++++++++++++----
 quantity.py   | 312 ++++++++++++++++++++++++++++++++++++++-----
 review.py     | 306 ++++++++++++++++++++++++++++++++----------
 4 files changed, 1090 insertions(+), 160 deletions(-)
10. remove
Date: 2025-10-22
Author: 5sudeng
Hash: 2c79055
Changes
"\breview.py" |  88 ----------------------------------------------------------
 .DS_Store     | Bin 0 -> 6148 bytes
 2 files changed, 88 deletions(-)
11. git ignore
Date: 2025-10-22
Author: 5sudeng
Hash: 92e5529
Changes
.gitignore | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)
12. Update products.csv with vendorItemId and itemId for existing products
Date: 2025-10-22
Author: ssunggun2
Hash: cb1be93
Changes
products.csv | 20 ++++++++++----------
 1 file changed, 10 insertions(+), 10 deletions(-)
13. add use example
Date: 2025-10-22
Author: 5sudeng
Hash: 561eac0
Changes
fetch_html.py | 19 +++++++++++++++++++
 1 file changed, 19 insertions(+)
14. add use example
Date: 2025-10-22
Author: 5sudeng
Hash: 67c46a8
Changes
inquiries.py | 21 +++++++++++++++++++--
 1 file changed, 19 insertions(+), 2 deletions(-)
15. debug & add use example
Date: 2025-10-22
Author: 5sudeng
Hash: bc8024b
Changes
quantity.py | 31 +++++++++++++++++++++++++++++++
 1 file changed, 31 insertions(+)
16. add use example
Date: 2025-10-22
Author: 5sudeng
Hash: 6bcc1ba
Changes
review.py | 21 +++++++++++++++++++--
 1 file changed, 19 insertions(+), 2 deletions(-)
17. raw data (10)
Date: 2025-10-22
Author: 5sudeng
Hash: f808939
Changes
outputs_html/response_1008978.html                 |    9 +
 outputs_html/response_185307349.html               |    9 +
 outputs_html/response_1912026433.html              |    9 +
 outputs_html/response_487322.html                  |    9 +
 outputs_html/response_7527803282.html              |    9 +
 outputs_html/response_7958974.html                 |    9 +
 outputs_html/response_8289731246.html              |    9 +
 outputs_html/response_86564.html                   |    9 +
 outputs_html/response_8826288636.html              |    9 +
 outputs_html/response_96571.html                   |    9 +
 outputs_html/summary.jsonl                         |   10 +
 .../inquiries_1008978_p1_1761131634795.json        |  195 +
 .../inquiries_185307349_p1_1761131649097.json      |  195 +
 .../inquiries_1912026433_p1_1761131642955.json     |  195 +
 .../inquiries_487322_p1_1761131632844.json         |  195 +
 .../inquiries_7527803282_p1_1761131636595.json     |  195 +
 .../inquiries_7958974_p1_1761131647340.json        |  195 +
 .../inquiries_8289731246_p1_1761131640707.json     |  169 +
 .../inquiries_86564_p1_1761131645429.json          |  195 +
 .../inquiries_8826288636_p1_1761131638883.json     |  195 +
 .../inquiries_96571_p1_1761131651568.json          |  195 +
 outputs_inquiries/inquiries_all.jsonl              |   10 +
 .../quantity_info_1008978_1761131816732.json       | 3320 +++++++++++++++++
 .../quantity_info_185307349_1761131836028.json     | 1275 +++++++
 .../quantity_info_1912026433_1761131827760.json    | 1893 ++++++++++
 .../quantity_info_487322_1761131814351.json        | 3864 ++++++++++++++++++++
 .../quantity_info_7527803282_1761131819852.json    | 3231 ++++++++++++++++
 .../quantity_info_7958974_1761131833531.json       | 1320 +++++++
 .../quantity_info_8289731246_1761131825093.json    | 1455 ++++++++
 .../quantity_info_86564_1761131830695.json         | 1494 ++++++++
 .../quantity_info_8826288636_1761131822964.json    | 1496 ++++++++
 .../quantity_info_96571_1761131838845.json         | 1721 +++++++++
 outputs_quantity/summary.jsonl                     |   10 +
 33 files changed, 23113 insertions(+)
18. update: use example (size)
Date: 2025-10-23
Author: 5sudeng
Hash: ecac983
Changes
review.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
19. update: review size
Date: 2025-10-23
Author: 5sudeng
Hash: 8789b25
Changes
products.csv | 2048 +++++++++++++++++++++++++++++-----------------------------
 1 file changed, 1024 insertions(+), 1024 deletions(-)
20. update: use example
Date: 2025-10-23
Author: 5sudeng
Hash: 54f84f4
Changes
review.py | 8 ++++----
 1 file changed, 4 insertions(+), 4 deletions(-)
21. raw data (10)
Date: 2025-10-23
Author: 5sudeng
Hash: 804c2e9
Changes
.../review_1008978_p1_1761179841642.json           | 4684 ++++++++++++++++++
 .../review_185307349_p1_1761179857267.json         | 4842 ++++++++++++++++++
 .../review_1912026433_p1_1761179850069.json        | 5001 +++++++++++++++++++
 .../review_487322_p1_1761179839080.json            | 5032 +++++++++++++++++++
 .../review_7527803282_p1_1761179843842.json        | 5081 +++++++++++++++++++
 .../review_7958974_p1_1761179854435.json           | 5087 +++++++++++++++++++
 .../review_8289731246_p1_1761179848009.json        | 4850 +++++++++++++++++++
 outputs_reviews/review_86564_p1_1761179851768.json | 5118 ++++++++++++++++++++
 .../review_8826288636_p1_1761179845940.json        | 4954 +++++++++++++++++++
 outputs_reviews/review_96571_p1_1761179859794.json | 5097 +++++++++++++++++++
 outputs_reviews/reviews.jsonl                      |   10 +
 11 files changed, 49756 insertions(+)
22. code: raw data to schema + image
Date: 2025-10-23
Author: 5sudeng
Hash: edb7588
Changes
to_schema.py | 365 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 365 insertions(+)
23. structured data
Date: 2025-10-23
Author: 5sudeng
Hash: 69e3fb0
Changes
.DS_Store                                          | Bin 6148 -> 6148 bytes
 .../1008978/image_manifest_1008978.json            |  64 ++
 .../1008978/images/html_1008978_d81189f1.jpg       | Bin 0 -> 66164 bytes
 outputs_structured/1008978/product_1008978.json    | 665 ++++++++++++++++
 .../1008978/reviews_1008978_p1.jsonl               |  30 +
 .../185307349/image_manifest_185307349.json        |  16 +
 .../185307349/images/html_185307349_57727e14.png   | Bin 0 -> 282046 bytes
 .../185307349/images/html_185307349_a54eba06.jpg   | Bin 0 -> 43258 bytes
 .../185307349/product_185307349.json               | 367 +++++++++
 .../185307349/reviews_185307349_p1.jsonl           |  30 +
 .../1912026433/image_manifest_1912026433.json      |  30 +
 .../1912026433/images/html_1912026433_e9168d53.jpg | Bin 0 -> 69367 bytes
 .../1912026433/product_1912026433.json             | 451 +++++++++++
 .../1912026433/reviews_1912026433_p1.jsonl         |  30 +
 .../487322/image_manifest_487322.json              | 172 +++++
 .../487322/images/html_487322_16e6a25c.jpg         | Bin 0 -> 58971 bytes
 .../487322/images/html_487322_1e08f8cb.png         | Bin 0 -> 50009 bytes
 .../487322/images/html_487322_6a66c558.png         | Bin 0 -> 275667 bytes
 .../487322/images/html_487322_6f2c710f.jpg         | Bin 0 -> 62131 bytes
 .../487322/images/html_487322_a11a8b10.png         | Bin 0 -> 292842 bytes
 .../487322/images/html_487322_ab3aacf8.png         | Bin 0 -> 109578 bytes
 .../487322/images/html_487322_b6580e76.jpg         | Bin 0 -> 43358 bytes
 .../487322/images/html_487322_f7e534b6.jpg         | Bin 0 -> 54447 bytes
 outputs_structured/487322/product_487322.json      | 853 +++++++++++++++++++++
 outputs_structured/487322/reviews_487322_p1.jsonl  |  30 +
 .../7527803282/image_manifest_7527803282.json      | 111 +++
 .../7527803282/images/html_7527803282_02129e5d.jpg | Bin 0 -> 47283 bytes
 .../7527803282/images/html_7527803282_1fdae95f.jpg | Bin 0 -> 40343 bytes
 .../7527803282/images/html_7527803282_25cd6739.jpg | Bin 0 -> 43140 bytes
 .../7527803282/images/html_7527803282_30d583d3.jpg | Bin 0 -> 58260 bytes
 .../7527803282/images/html_7527803282_c2f4c609.png | Bin 0 -> 211482 bytes
 .../7527803282/images/html_7527803282_d02ed6f4.png | Bin 0 -> 262271 bytes
 .../7527803282/images/html_7527803282_d07e7276.jpg | Bin 0 -> 28815 bytes
 .../7527803282/product_7527803282.json             | 712 +++++++++++++++++
 .../7527803282/reviews_7527803282_p1.jsonl         |  30 +
 .../7958974/image_manifest_7958974.json            |  40 +
 .../7958974/images/html_7958974_0447624a.jpg       | Bin 0 -> 80487 bytes
 outputs_structured/7958974/product_7958974.json    | 411 ++++++++++
 .../7958974/reviews_7958974_p1.jsonl               |  30 +
 .../8289731246/image_manifest_8289731246.json      |  41 +
 .../8289731246/images/html_8289731246_037e481f.png | Bin 0 -> 436610 bytes
 .../8289731246/images/html_8289731246_5d087196.jpg | Bin 0 -> 54971 bytes
 .../8289731246/images/html_8289731246_68d3dbbc.png | Bin 0 -> 411331 bytes
 .../8289731246/images/html_8289731246_7d3ebffb.png | Bin 0 -> 416431 bytes
 .../8289731246/images/html_8289731246_dc6d33fa.png | Bin 0 -> 243793 bytes
 .../8289731246/images/html_8289731246_f743b6d2.png | Bin 0 -> 82023 bytes
 .../8289731246/product_8289731246.json             | 399 ++++++++++
 .../8289731246/reviews_8289731246_p1.jsonl         |  30 +
 outputs_structured/86564/image_manifest_86564.json |  76 ++
 .../86564/images/html_86564_4aa44c45.jpg           | Bin 0 -> 68893 bytes
 .../86564/images/html_86564_5b601ed9.jpg           | Bin 0 -> 78445 bytes
 .../86564/images/html_86564_60b8b958.jpg           | Bin 0 -> 54684 bytes
 .../86564/images/html_86564_d59c0009.jpg           | Bin 0 -> 72244 bytes
 .../86564/images/html_86564_ecce228b.jpg           | Bin 0 -> 41161 bytes
 outputs_structured/86564/product_86564.json        | 457 +++++++++++
 outputs_structured/86564/reviews_86564_p1.jsonl    |  30 +
 .../8826288636/image_manifest_8826288636.json      |  61 ++
 .../8826288636/images/html_8826288636_291e2a33.jpg | Bin 0 -> 54842 bytes
 .../8826288636/images/html_8826288636_7c0e0781.jpg | Bin 0 -> 58516 bytes
 .../8826288636/images/html_8826288636_c6ba2a61.jpg | Bin 0 -> 66355 bytes
 .../8826288636/images/html_8826288636_d8b91a26.png | Bin 0 -> 224437 bytes
 .../8826288636/images/html_8826288636_f4544cd4.png | Bin 0 -> 202746 bytes
 .../8826288636/product_8826288636.json             | 432 +++++++++++
 .../8826288636/reviews_8826288636_p1.jsonl         |  30 +
 outputs_structured/96571/image_manifest_96571.json |  93 +++
 .../96571/images/html_96571_2baba90d.png           | Bin 0 -> 231092 bytes
 .../96571/images/html_96571_9a5fe554.png           | Bin 0 -> 283646 bytes
 .../96571/images/html_96571_a1a70111.png           | Bin 0 -> 269069 bytes
 .../96571/images/html_96571_b683fef0.jpg           | Bin 0 -> 59419 bytes
 .../96571/images/html_96571_c995b5b6.png           | Bin 0 -> 221416 bytes
 .../96571/images/html_96571_cddcc89a.png           | Bin 0 -> 311385 bytes
 .../96571/images/html_96571_d2a36e53.png           | Bin 0 -> 344828 bytes
 outputs_structured/96571/product_96571.json        | 504 ++++++++++++
 outputs_structured/96571/reviews_96571_p1.jsonl    |  30 +
 74 files changed, 6255 insertions(+)
24. move files
Date: 2025-10-23
Author: 5sudeng
Hash: 4498717
Changes
.../crawl_category_urls.py                         |   0
 fetch_html.py => crawling/fetch_html.py            |   0
 inquiries.py => crawling/inquiries.py              |   0
 .../make_products_csv.py                           |   0
 quantity.py => crawling/quantity.py                |   0
 review.py => crawling/review.py                    |   0
 .../outputs_html}/response_1008978.html            |   0
 .../outputs_html}/response_185307349.html          |   0
 .../outputs_html}/response_1912026433.html         |   0
 .../outputs_html}/response_487322.html             |   0
 .../outputs_html}/response_7527803282.html         |   0
 .../outputs_html}/response_7958974.html            |   0
 .../outputs_html}/response_8289731246.html         |   0
 .../outputs_html}/response_86564.html              |   0
 .../outputs_html}/response_8826288636.html         |   0
 .../outputs_html}/response_96571.html              |   0
 {outputs_html => data/outputs_html}/summary.jsonl  |   0
 .../inquiries_1008978_p1_1761131634795.json        |   0
 .../inquiries_185307349_p1_1761131649097.json      |   0
 .../inquiries_1912026433_p1_1761131642955.json     |   0
 .../inquiries_487322_p1_1761131632844.json         |   0
 .../inquiries_7527803282_p1_1761131636595.json     |   0
 .../inquiries_7958974_p1_1761131647340.json        |   0
 .../inquiries_8289731246_p1_1761131640707.json     |   0
 .../inquiries_86564_p1_1761131645429.json          |   0
 .../inquiries_8826288636_p1_1761131638883.json     |   0
 .../inquiries_96571_p1_1761131651568.json          |   0
 .../outputs_inquiries}/inquiries_all.jsonl         |   0
 .../quantity_info_1008978_1761131816732.json       |   0
 .../quantity_info_185307349_1761131836028.json     |   0
 .../quantity_info_1912026433_1761131827760.json    |   0
 .../quantity_info_487322_1761131814351.json        |   0
 .../quantity_info_7527803282_1761131819852.json    |   0
 .../quantity_info_7958974_1761131833531.json       |   0
 .../quantity_info_8289731246_1761131825093.json    |   0
 .../quantity_info_86564_1761131830695.json         |   0
 .../quantity_info_8826288636_1761131822964.json    |   0
 .../quantity_info_96571_1761131838845.json         |   0
 .../outputs_quantity}/summary.jsonl                |   0
 .../review_1008978_p1_1761179841642.json           |   0
 .../review_185307349_p1_1761179857267.json         |   0
 .../review_1912026433_p1_1761179850069.json        |   0
 .../review_487322_p1_1761179839080.json            |   0
 .../review_7527803282_p1_1761179843842.json        |   0
 .../review_7958974_p1_1761179854435.json           |   0
 .../review_8289731246_p1_1761179848009.json        |   0
 .../review_86564_p1_1761179851768.json             |   0
 .../review_8826288636_p1_1761179845940.json        |   0
 .../review_96571_p1_1761179859794.json             |   0
 .../outputs_reviews}/reviews.jsonl                 |   0
 .../1008978/image_manifest_1008978.json            |   0
 .../1008978/images/html_1008978_d81189f1.jpg       | Bin
 .../1008978/product_1008978.json                   |   0
 .../1008978/reviews_1008978_p1.jsonl               |   0
 .../185307349/image_manifest_185307349.json        |   0
 .../185307349/images/html_185307349_57727e14.png   | Bin
 .../185307349/images/html_185307349_a54eba06.jpg   | Bin
 .../185307349/product_185307349.json               |   0
 .../185307349/reviews_185307349_p1.jsonl           |   0
 .../1912026433/image_manifest_1912026433.json      |   0
 .../1912026433/images/html_1912026433_e9168d53.jpg | Bin
 .../1912026433/product_1912026433.json             |   0
 .../1912026433/reviews_1912026433_p1.jsonl         |   0
 .../487322/image_manifest_487322.json              |   0
 .../487322/images/html_487322_16e6a25c.jpg         | Bin
 .../487322/images/html_487322_1e08f8cb.png         | Bin
 .../487322/images/html_487322_6a66c558.png         | Bin
 .../487322/images/html_487322_6f2c710f.jpg         | Bin
 .../487322/images/html_487322_a11a8b10.png         | Bin
 .../487322/images/html_487322_ab3aacf8.png         | Bin
 .../487322/images/html_487322_b6580e76.jpg         | Bin
 .../487322/images/html_487322_f7e534b6.jpg         | Bin
 .../outputs_structured}/487322/product_487322.json |   0
 .../487322/reviews_487322_p1.jsonl                 |   0
 .../7527803282/image_manifest_7527803282.json      |   0
 .../7527803282/images/html_7527803282_02129e5d.jpg | Bin
 .../7527803282/images/html_7527803282_1fdae95f.jpg | Bin
 .../7527803282/images/html_7527803282_25cd6739.jpg | Bin
 .../7527803282/images/html_7527803282_30d583d3.jpg | Bin
 .../7527803282/images/html_7527803282_c2f4c609.png | Bin
 .../7527803282/images/html_7527803282_d02ed6f4.png | Bin
 .../7527803282/images/html_7527803282_d07e7276.jpg | Bin
 .../7527803282/product_7527803282.json             |   0
 .../7527803282/reviews_7527803282_p1.jsonl         |   0
 .../7958974/image_manifest_7958974.json            |   0
 .../7958974/images/html_7958974_0447624a.jpg       | Bin
 .../7958974/product_7958974.json                   |   0
 .../7958974/reviews_7958974_p1.jsonl               |   0
 .../8289731246/image_manifest_8289731246.json      |   0
 .../8289731246/images/html_8289731246_037e481f.png | Bin
 .../8289731246/images/html_8289731246_5d087196.jpg | Bin
 .../8289731246/images/html_8289731246_68d3dbbc.png | Bin
 .../8289731246/images/html_8289731246_7d3ebffb.png | Bin
 .../8289731246/images/html_8289731246_dc6d33fa.png | Bin
 .../8289731246/images/html_8289731246_f743b6d2.png | Bin
 .../8289731246/product_8289731246.json             |   0
 .../8289731246/reviews_8289731246_p1.jsonl         |   0
 .../86564/image_manifest_86564.json                |   0
 .../86564/images/html_86564_4aa44c45.jpg           | Bin
 .../86564/images/html_86564_5b601ed9.jpg           | Bin
 .../86564/images/html_86564_60b8b958.jpg           | Bin
 .../86564/images/html_86564_d59c0009.jpg           | Bin
 .../86564/images/html_86564_ecce228b.jpg           | Bin
 .../outputs_structured}/86564/product_86564.json   |   0
 .../86564/reviews_86564_p1.jsonl                   |   0
 .../8826288636/image_manifest_8826288636.json      |   0
 .../8826288636/images/html_8826288636_291e2a33.jpg | Bin
 .../8826288636/images/html_8826288636_7c0e0781.jpg | Bin
 .../8826288636/images/html_8826288636_c6ba2a61.jpg | Bin
 .../8826288636/images/html_8826288636_d8b91a26.png | Bin
 .../8826288636/images/html_8826288636_f4544cd4.png | Bin
 .../8826288636/product_8826288636.json             |   0
 .../8826288636/reviews_8826288636_p1.jsonl         |   0
 .../96571/image_manifest_96571.json                |   0
 .../96571/images/html_96571_2baba90d.png           | Bin
 .../96571/images/html_96571_9a5fe554.png           | Bin
 .../96571/images/html_96571_a1a70111.png           | Bin
 .../96571/images/html_96571_b683fef0.jpg           | Bin
 .../96571/images/html_96571_c995b5b6.png           | Bin
 .../96571/images/html_96571_cddcc89a.png           | Bin
 .../96571/images/html_96571_d2a36e53.png           | Bin
 .../outputs_structured}/96571/product_96571.json   |   0
 .../96571/reviews_96571_p1.jsonl                   |   0
 products.csv => data/products.csv                  |   0
 test.py                                            | 163 ---------------------
 125 files changed, 163 deletions(-)
25. README
Date: 2025-10-23
Author: 5sudeng
Hash: b9e02fa
Changes
README.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
26. refactor: improve code structure and error handling in crawl_category_urls.py
Date: 2025-10-25
Author: ssunggun2
Hash: 0616a51
Changes
crawling/crawl_category_urls.py | 232 ++++++++++++++++++++++------------------
 1 file changed, 127 insertions(+), 105 deletions(-)
27. refactor: enhance make_products_csv.py with improved ID extraction, error handling, and command-line argument parsing
Date: 2025-10-25
Author: ssunggun2
Hash: 4f3093d
Changes
crawling/make_products_csv.py | 378 ++++++++++++++++++++++++++----------------
 1 file changed, 236 insertions(+), 142 deletions(-)
28. refactor: streamline fetch_html.py with improved structure, enhanced error handling, and added support for HTTP/2 requests
Date: 2025-10-25
Author: ssunggun2
Hash: 7578351
Changes
crawling/fetch_html.py | 563 +++++++++++++++++++++----------------------------
 1 file changed, 237 insertions(+), 326 deletions(-)
29. refactor: simplify inquiries.py with improved structure, enhanced cookie handling, and added session management for requests
Date: 2025-10-25
Author: ssunggun2
Hash: fcd31cd
Changes
crawling/inquiries.py | 167 ++++++++++++++++++++++----------------------------
 1 file changed, 72 insertions(+), 95 deletions(-)
30. refactor: enhance quantity.py with improved structure, robust error handling, and added support for multiple request methods
Date: 2025-10-25
Author: ssunggun2
Hash: accc206
Changes
crawling/quantity.py | 475 ++++++++++++++++++++++++++-------------------------
 1 file changed, 244 insertions(+), 231 deletions(-)
31. refactor: improve review.py with enhanced structure, robust error handling, and added support for session management and IPv4-only resolution
Date: 2025-10-25
Author: ssunggun2
Hash: e60ff3b
Changes
crawling/review.py | 193 +++++++++++++++++++++++++----------------------------
 1 file changed, 92 insertions(+), 101 deletions(-)
32. test: add test script for Coupang Crawling Pipeline to verify functionality and configuration
Date: 2025-10-25
Author: ssunggun2
Hash: dd2c45c
Changes
crawling/test_pipeline.py | 140 ++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 140 insertions(+)
33. feat: implement Coupang Crawling Pipeline orchestrating multiple data extraction steps from category URLs to product details
Date: 2025-10-25
Author: ssunggun2
Hash: 7a22aa9
Changes
crawling/main.py | 437 +++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 437 insertions(+)
34. docs: add comprehensive README for Coupang Crawling Pipeline detailing usage, configuration options, and troubleshooting
Date: 2025-10-25
Author: ssunggun2
Hash: a37bc44
Changes
crawling/README.md | 164 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 164 insertions(+)
35. feat: add run script to initiate the Coupang Crawling Pipeline with category URL and cookie file configuration
Date: 2025-10-25
Author: ssunggun2
Hash: fd9e9c0
Changes
run.sh | 3 +++
 1 file changed, 3 insertions(+)
36. refactor: restructure main.py for improved readability and maintainability, enhancing cookie handling and step orchestration without sys.argv mutation
Date: 2025-10-25
Author: ssunggun2
Hash: f92a902
Changes
crawling/main.py | 633 ++++++++++++++++++++++++++++---------------------------
 1 file changed, 322 insertions(+), 311 deletions(-)
37. refactor: standardize argument naming conventions across crawling scripts for consistency and clarity
Date: 2025-10-25
Author: ssunggun2
Hash: 24fc3c0
Changes
crawling/crawl_category_urls.py | 14 ++++++-------
 crawling/inquiries.py           | 12 +++++------
 crawling/main.py                | 44 ++++++++++++++++++++---------------------
 crawling/quantity.py            | 12 +++++------
 crawling/review.py              | 10 +++++-----
 5 files changed, 46 insertions(+), 46 deletions(-)
38. feat: enhance Coupang Crawling Pipeline with improved error handling, cookie support, and configurable timeouts for page fetching
Date: 2025-10-25
Author: ssunggun2
Hash: c86371c
Changes
crawling/main.py          | 49 +++++++++++++++++++++++++++++++----------------
 crawling/test_pipeline.py |  2 +-
 2 files changed, 33 insertions(+), 18 deletions(-)
39. feat: add new data processing scripts for structured JSON output and chunking of product data, enhancing the Coupang Crawling Pipeline
Date: 2025-10-27
Author: ssunggun2
Hash: ab7243d
Changes
.gitignore                               |    4 +-
 crawling/btf.py                          |  317 +++++++++
 crawling/crawl_category_urls.py          |   86 ++-
 crawling/main.py                         |   70 +-
 data/products.csv                        | 1015 +----------------------------
 data/products1.csv                       | 1025 ++++++++++++++++++++++++++++++
 preprocessing/data_chunking_processor.py |  545 ++++++++++++++++
 preprocessing/to_schema_plus_btf.py      |  510 +++++++++++++++
 products.csv                             |   12 +
 9 files changed, 2529 insertions(+), 1055 deletions(-)
40. chore: update .gitignore to include Python bytecode files (*.pyc) for cleaner repository management
Date: 2025-10-27
Author: ssunggun2
Hash: 317e572
Changes
.gitignore | 1 +
 1 file changed, 1 insertion(+)
41. feat: add new structured JSON and BTF output files for various products, enhancing data extraction capabilities in the Coupang Crawling Pipeline
Date: 2025-10-27
Author: ssunggun2
Hash: 0b239f5
Changes
.DS_Store                                          | Bin 6148 -> 6148 bytes
 data/exports_normalized/chunked_data_output.json   | 485 +++++++++++++++++++++
 data/outputs_btf/all_btf.jsonl                     |  12 +
 ...008978_i4242032_v92843978880_1761547256920.json | 166 +++++++
 ...49_i25790113038_v92777883529_1761547269041.json | 118 +++++
 ...433_i3461482826_v86273585306_1761547264197.json | 142 ++++++
 ...tf_487322_i41045_v3000080400_1761547255093.json | 166 +++++++
 ...601_i9133866797_v79544780492_1761481020665.json | 130 ++++++
 ...601_i9133866797_v79544780492_1761547272871.json | 130 ++++++
 ...3282_i264019241_v91164580247_1761547258959.json | 142 ++++++
 ...f_7958974_i93553_v3000207618_1761547266997.json | 130 ++++++
 ...46_i23467099110_v90766226334_1761547262359.json | 130 ++++++
 ...tf_86564_i175470_v3000104081_1761547265549.json | 178 ++++++++
 ...636_i25720037760_v3000141660_1761547260276.json | 130 ++++++
 ..._96571_i1043420_v84993758114_1761547271197.json | 130 ++++++
 .../1008978/image_manifest_1008978.json            | 120 ++---
 .../1008978/product_1008978.json                   | 135 +++---
 .../185307349/image_manifest_185307349.json        |  19 +-
 .../185307349/product_185307349.json               |  34 +-
 .../1912026433/image_manifest_1912026433.json      |  52 ++-
 .../1912026433/product_1912026433.json             |  67 +--
 .../487322/image_manifest_487322.json              | 318 +++++++-------
 data/outputs_structured/487322/product_487322.json | 333 +++++++-------
 .../7527803282/image_manifest_7527803282.json      | 195 ++++-----
 .../7527803282/product_7527803282.json             | 210 ++++-----
 .../7958974/image_manifest_7958974.json            |  69 +--
 .../7958974/product_7958974.json                   |  84 ++--
 .../8289731246/image_manifest_8289731246.json      |  58 ++-
 .../8289731246/product_8289731246.json             |  73 ++--
 .../86564/image_manifest_86564.json                | 135 +++---
 data/outputs_structured/86564/product_86564.json   | 150 ++++---
 .../8826288636/image_manifest_8826288636.json      | 101 +++--
 .../8826288636/product_8826288636.json             | 116 ++---
 .../96571/image_manifest_96571.json                | 159 ++++---
 data/outputs_structured/96571/product_96571.json   | 174 ++++----
 outputs/html/summary.jsonl                         |   1 +
 36 files changed, 3530 insertions(+), 1262 deletions(-)
42. ocr rag add
Date: 2025-10-28
Author: bae4147
Hash: 9bc21e3
Changes
.env                                               |   1 +
 data/outputs_structured/1008978/ocrs_1008978.json  |   6 +
 .../185307349/ocrs_185307349.json                  |  10 ++
 .../1912026433/ocrs_1912026433.json                |   6 +
 data/outputs_structured/487322/ocrs_487322.json    |  34 ++++
 .../7527803282/ocrs_7527803282.json                |  30 ++++
 data/outputs_structured/7958974/ocrs_7958974.json  |   6 +
 .../8289731246/ocrs_8289731246.json                |  26 +++
 data/outputs_structured/86564/ocrs_86564.json      |  22 +++
 .../8826288636/ocrs_8826288636.json                |  22 +++
 data/outputs_structured/96571/ocrs_96571.json      |  30 ++++
 ocr.py                                             |  55 ++++++
 .../inquiries_8250433942_p1_1761113173275.json     | 144 +++++++++++++++
 .../1008978/image_manifest_1008978.json            |  64 +++++++
 outputs_structured/1008978/product_1008978.json    |  87 +++++++++
 .../185307349/image_manifest_185307349.json        |  16 ++
 .../185307349/product_185307349.json               |  39 +++++
 .../1912026433/image_manifest_1912026433.json      |  30 ++++
 .../1912026433/product_1912026433.json             |  53 ++++++
 .../487322/image_manifest_487322.json              | 172 ++++++++++++++++++
 outputs_structured/487322/product_487322.json      | 195 +++++++++++++++++++++
 .../7527803282/image_manifest_7527803282.json      | 111 ++++++++++++
 .../7527803282/product_7527803282.json             | 134 ++++++++++++++
 .../7958974/image_manifest_7958974.json            |  40 +++++
 outputs_structured/7958974/product_7958974.json    |  63 +++++++
 .../8289731246/image_manifest_8289731246.json      |  41 +++++
 .../8289731246/product_8289731246.json             |  64 +++++++
 outputs_structured/86564/image_manifest_86564.json |  76 ++++++++
 outputs_structured/86564/product_86564.json        |  99 +++++++++++
 .../8826288636/image_manifest_8826288636.json      |  61 +++++++
 .../8826288636/product_8826288636.json             |  84 +++++++++
 outputs_structured/96571/image_manifest_96571.json |  93 ++++++++++
 outputs_structured/96571/product_96571.json        | 116 ++++++++++++
 requirements.txt                                   |  11 ++
 to_schema.py                                       |   2 +-
 35 files changed, 2042 insertions(+), 1 deletion(-)
43. rag 구현
Date: 2025-10-29
Author: bae4147
Hash: 7f39ab6
Changes
rag/README.md                                      | 396 +++++++++++++
 rag/analyze_chunks_final.py                        | 228 ++++++++
 rag/questions.txt                                  |  11 +
 rag/rag_cache_products/8826288636/image_store.pkl  | Bin 0 -> 29897 bytes
 .../8826288636/ocr_store/index.faiss               | Bin 0 -> 3117 bytes
 .../8826288636/ocr_store/index.pkl                 | Bin 0 -> 654 bytes
 .../8826288636/product_store/index.faiss           | Bin 0 -> 7725 bytes
 .../8826288636/product_store/index.pkl             | Bin 0 -> 1228 bytes
 .../8826288636/review_store/index.faiss            | Bin 0 -> 46125 bytes
 .../8826288636/review_store/index.pkl              | Bin 0 -> 71077 bytes
 rag/rag_with_detail.py                             | 622 +++++++++++++++++++++
 requirements.txt => rag/requirements.txt           |   0
 12 files changed, 1257 insertions(+)
44. image
Date: 2025-10-29
Author: ssunggun2
Hash: 56bf783
Changes
.gitignore                                         |   3 -
 .../1008978/images/btf_1008978_253ff7bf.jpg        | Bin 0 -> 41139 bytes
 .../1008978/images/btf_1008978_44d79454.JPG        | Bin 0 -> 61756 bytes
 .../1008978/images/btf_1008978_579f5b45.JPG        | Bin 0 -> 188479 bytes
 .../1008978/images/btf_1008978_81b07d6f.jpg        | Bin 0 -> 962501 bytes
 .../1008978/images/html_1008978_0b0d04c6.jpg       | Bin 0 -> 18006 bytes
 .../1008978/images/html_1008978_0b239a88.png       | Bin 0 -> 316179 bytes
 .../1008978/images/html_1008978_0c4cf627.jpg       | Bin 0 -> 26426 bytes
 .../1008978/images/html_1008978_0d4c5d29.jpg       | Bin 0 -> 95035 bytes
 .../1008978/images/html_1008978_0e3c3a70.jpg       | Bin 0 -> 21336 bytes
 .../1008978/images/html_1008978_0f15bc88.png       | Bin 0 -> 89033 bytes
 .../1008978/images/html_1008978_0fe57471.jpg       | Bin 0 -> 15978 bytes
 .../1008978/images/html_1008978_145b31f7.png       | Bin 0 -> 76379 bytes
 .../1008978/images/html_1008978_222bdf89.jpg       | Bin 0 -> 24302 bytes
 .../1008978/images/html_1008978_2de72783.jpg       | Bin 0 -> 1553 bytes
 .../1008978/images/html_1008978_314878ca.png       | Bin 0 -> 4201 bytes
 .../1008978/images/html_1008978_34a40098.png       | Bin 0 -> 4383 bytes
 .../1008978/images/html_1008978_35b7c450.jpg       | Bin 0 -> 2244 bytes
 .../1008978/images/html_1008978_3a0a05db.png       | Bin 0 -> 4408 bytes
 .../1008978/images/html_1008978_3ad4c9a8.jpg       | Bin 0 -> 90076 bytes
 .../1008978/images/html_1008978_425d55bc.jpg       | Bin 0 -> 2258 bytes
 .../1008978/images/html_1008978_45bc5d51.jpg       | Bin 0 -> 81240 bytes
 .../1008978/images/html_1008978_4abc83a8.jpg       | Bin 0 -> 22544 bytes
 .../1008978/images/html_1008978_4b4c8867.jpg       | Bin 0 -> 77842 bytes
 .../1008978/images/html_1008978_5c52a1ff.png       | Bin 0 -> 80494 bytes
 .../1008978/images/html_1008978_5e4859cf.jpg       | Bin 0 -> 32810 bytes
 .../1008978/images/html_1008978_65feb26d.jpg       | Bin 0 -> 98650 bytes
 .../1008978/images/html_1008978_6ef56e7b.png       | Bin 0 -> 379268 bytes
 .../1008978/images/html_1008978_76477606.jpg       | Bin 0 -> 13458 bytes
 .../1008978/images/html_1008978_78022fd4.jpg       | Bin 0 -> 2104 bytes
 .../1008978/images/html_1008978_7e39a2e7.png       | Bin 0 -> 4152 bytes
 .../1008978/images/html_1008978_806beec5.jpg       | Bin 0 -> 18472 bytes
 .../1008978/images/html_1008978_81662891.jpg       | Bin 0 -> 92931 bytes
 .../1008978/images/html_1008978_88ff8e5a.jpg       | Bin 0 -> 27268 bytes
 .../1008978/images/html_1008978_8babb78c.jpg       | Bin 0 -> 89623 bytes
 .../1008978/images/html_1008978_8c86bbb5.jpg       | Bin 0 -> 83093 bytes
 .../1008978/images/html_1008978_9a117d6b.png       | Bin 0 -> 295918 bytes
 .../1008978/images/html_1008978_9c0c0ddc.jpg       | Bin 0 -> 25217 bytes
 .../1008978/images/html_1008978_9d110487.jpg       | Bin 0 -> 2444 bytes
 .../1008978/images/html_1008978_a0bce8ad.jpg       | Bin 0 -> 35554 bytes
 .../1008978/images/html_1008978_a76639b8.jpg       | Bin 0 -> 36446 bytes
 .../1008978/images/html_1008978_a935f17d.jpg       | Bin 0 -> 2365 bytes
 .../1008978/images/html_1008978_ac086dbe.jpg       | Bin 0 -> 97637 bytes
 .../1008978/images/html_1008978_b9dc86a4.jpg       | Bin 0 -> 19084 bytes
 .../1008978/images/html_1008978_bbcaacb1.jpg       | Bin 0 -> 15995 bytes
 .../1008978/images/html_1008978_bdf1710e.png       | Bin 0 -> 325984 bytes
 .../1008978/images/html_1008978_c3c2d050.png       | Bin 0 -> 73255 bytes
 .../1008978/images/html_1008978_c40e171f.png       | Bin 0 -> 4430 bytes
 .../1008978/images/html_1008978_ca4cf8f8.jpg       | Bin 0 -> 89072 bytes
 .../1008978/images/html_1008978_cbba8c97.jpg       | Bin 0 -> 36548 bytes
 .../1008978/images/html_1008978_d20caed9.png       | Bin 0 -> 74175 bytes
 .../1008978/images/html_1008978_d2915946.png       | Bin 0 -> 295733 bytes
 .../1008978/images/html_1008978_d6856877.jpg       | Bin 0 -> 35644 bytes
 .../1008978/images/html_1008978_d7d6bc87.jpg       | Bin 0 -> 15720 bytes
 .../1008978/images/html_1008978_dfc2a865.jpg       | Bin 0 -> 2159 bytes
 .../1008978/images/html_1008978_e1cef2f2.png       | Bin 0 -> 5264 bytes
 .../1008978/images/html_1008978_e5ead054.jpg       | Bin 0 -> 33174 bytes
 .../1008978/images/html_1008978_e7345a57.png       | Bin 0 -> 78020 bytes
 .../1008978/images/html_1008978_eb1b28b9.png       | Bin 0 -> 311775 bytes
 .../1008978/images/html_1008978_efe813f2.jpg       | Bin 0 -> 94185 bytes
 .../1008978/images/html_1008978_ff24d269.jpg       | Bin 0 -> 72262 bytes
 .../185307349/images/btf_185307349_97740bc0.jpg    | Bin 0 -> 423680 bytes
 .../185307349/images/html_185307349_0803a614.jpg   | Bin 0 -> 1868 bytes
 .../185307349/images/html_185307349_10d60c47.png   | Bin 0 -> 86947 bytes
 .../185307349/images/html_185307349_7e27ee5d.png   | Bin 0 -> 4556 bytes
 .../185307349/images/html_185307349_88e6cced.png   | Bin 0 -> 4923 bytes
 .../185307349/images/html_185307349_a1c6c7df.png   | Bin 0 -> 344272 bytes
 .../185307349/images/html_185307349_cbc811c6.jpg   | Bin 0 -> 14736 bytes
 .../185307349/images/html_185307349_e1143b99.png   | Bin 0 -> 71821 bytes
 .../1912026433/images/btf_1912026433_253ff7bf.jpg  | Bin 0 -> 41139 bytes
 .../1912026433/images/btf_1912026433_b67c5f7e.jpg  | Bin 0 -> 921162 bytes
 .../1912026433/images/btf_1912026433_d5062fd5.jpg  | Bin 0 -> 41119 bytes
 .../1912026433/images/html_1912026433_0af1955c.jpg | Bin 0 -> 56723 bytes
 .../1912026433/images/html_1912026433_0cd340e3.jpg | Bin 0 -> 19332 bytes
 .../1912026433/images/html_1912026433_0f1adf55.jpg | Bin 0 -> 69367 bytes
 .../1912026433/images/html_1912026433_18b82c1e.jpg | Bin 0 -> 12792 bytes
 .../1912026433/images/html_1912026433_1ab62e8a.jpg | Bin 0 -> 15016 bytes
 .../1912026433/images/html_1912026433_219ef255.jpg | Bin 0 -> 1636 bytes
 .../1912026433/images/html_1912026433_3e471bf4.jpg | Bin 0 -> 56731 bytes
 .../1912026433/images/html_1912026433_5249f90e.jpg | Bin 0 -> 29430 bytes
 .../1912026433/images/html_1912026433_55ff25fd.jpg | Bin 0 -> 32282 bytes
 .../1912026433/images/html_1912026433_56d4d3a7.jpg | Bin 0 -> 1364 bytes
 .../1912026433/images/html_1912026433_5b82b29d.jpg | Bin 0 -> 12792 bytes
 .../1912026433/images/html_1912026433_62f16b5b.jpg | Bin 0 -> 78638 bytes
 .../1912026433/images/html_1912026433_6ae3b9e2.jpg | Bin 0 -> 15002 bytes
 .../1912026433/images/html_1912026433_7bb3e8e4.jpg | Bin 0 -> 18076 bytes
 .../1912026433/images/html_1912026433_88ebdc95.jpg | Bin 0 -> 1663 bytes
 .../1912026433/images/html_1912026433_99d94f16.jpg | Bin 0 -> 32592 bytes
 .../1912026433/images/html_1912026433_ae994ae6.jpg | Bin 0 -> 79025 bytes
 .../1912026433/images/html_1912026433_c0766fb9.jpg | Bin 0 -> 29430 bytes
 .../1912026433/images/html_1912026433_c26d884b.jpg | Bin 0 -> 29430 bytes
 .../1912026433/images/html_1912026433_c3e825c5.jpg | Bin 0 -> 66626 bytes
 .../1912026433/images/html_1912026433_e0ca4c22.jpg | Bin 0 -> 17893 bytes
 .../1912026433/images/html_1912026433_e5370cfe.jpg | Bin 0 -> 12792 bytes
 .../1912026433/images/html_1912026433_f1918208.jpg | Bin 0 -> 69367 bytes
 .../487322/images/btf_487322_253ff7bf.jpg          | Bin 0 -> 41139 bytes
 .../487322/images/btf_487322_367b0666.jpg          | Bin 0 -> 104490 bytes
 .../487322/images/btf_487322_410cd1f1.jpg          | Bin 0 -> 736702 bytes
 .../487322/images/btf_487322_457ef74f.jpg          | Bin 0 -> 545430 bytes
 .../487322/images/btf_487322_5f43cda2.jpg          | Bin 0 -> 14867 bytes
 .../487322/images/btf_487322_c1fc1be8.jpg          | Bin 0 -> 761954 bytes
 .../487322/images/html_487322_0182bb8a.png         | Bin 0 -> 1941 bytes
 .../487322/images/html_487322_0265172c.png         | Bin 0 -> 60833 bytes
 .../487322/images/html_487322_04bacf68.png         | Bin 0 -> 292842 bytes
 .../487322/images/html_487322_070214f9.jpg         | Bin 0 -> 43735 bytes
 .../487322/images/html_487322_070bec41.jpg         | Bin 0 -> 49946 bytes
 .../487322/images/html_487322_089f1d5b.jpg         | Bin 0 -> 14713 bytes
 .../487322/images/html_487322_08cea9ed.png         | Bin 0 -> 71410 bytes
 .../487322/images/html_487322_0ada8428.png         | Bin 0 -> 4004 bytes
 .../487322/images/html_487322_0b24554f.png         | Bin 0 -> 60742 bytes
 .../487322/images/html_487322_0be5040e.png         | Bin 0 -> 4503 bytes
 .../487322/images/html_487322_0d00b705.png         | Bin 0 -> 4346 bytes
 .../487322/images/html_487322_0d5c407f.jpg         | Bin 0 -> 1857 bytes
 .../487322/images/html_487322_0da66cbd.jpg         | Bin 0 -> 1884 bytes
 .../487322/images/html_487322_0de00340.jpg         | Bin 0 -> 20389 bytes
 .../487322/images/html_487322_0e1f6359.png         | Bin 0 -> 4268 bytes
 .../487322/images/html_487322_0e6c3217.png         | Bin 0 -> 272171 bytes
 .../487322/images/html_487322_0fab428d.png         | Bin 0 -> 70247 bytes
 .../487322/images/html_487322_10b2583a.png         | Bin 0 -> 4268 bytes
 .../487322/images/html_487322_11cd7b53.png         | Bin 0 -> 224647 bytes
 .../487322/images/html_487322_14bdef31.png         | Bin 0 -> 52195 bytes
 .../487322/images/html_487322_15098ef7.jpg         | Bin 0 -> 60347 bytes
 .../487322/images/html_487322_19225efb.jpg         | Bin 0 -> 1253 bytes
 .../487322/images/html_487322_19ef9d94.png         | Bin 0 -> 268666 bytes
 .../487322/images/html_487322_1b163cac.jpg         | Bin 0 -> 49607 bytes
 .../487322/images/html_487322_1f079ca7.png         | Bin 0 -> 51948 bytes
 .../487322/images/html_487322_20ccba03.png         | Bin 0 -> 70247 bytes
 .../487322/images/html_487322_25174fc5.png         | Bin 0 -> 4568 bytes
 .../487322/images/html_487322_26610291.jpg         | Bin 0 -> 1349 bytes
 .../487322/images/html_487322_276cc3d0.jpg         | Bin 0 -> 1401 bytes
 .../487322/images/html_487322_2ad22e5d.jpg         | Bin 0 -> 14770 bytes
 .../487322/images/html_487322_2b86e58b.png         | Bin 0 -> 182992 bytes
 .../487322/images/html_487322_2d71b650.png         | Bin 0 -> 13453 bytes
 .../487322/images/html_487322_2e8d4d70.png         | Bin 0 -> 68609 bytes
 .../487322/images/html_487322_2fa95fdb.jpg         | Bin 0 -> 1540 bytes
 .../487322/images/html_487322_346d84a3.png         | Bin 0 -> 4784 bytes
 .../487322/images/html_487322_3899727b.jpg         | Bin 0 -> 54371 bytes
 .../487322/images/html_487322_39aad83a.jpg         | Bin 0 -> 1256 bytes
 .../487322/images/html_487322_3ac41877.png         | Bin 0 -> 281690 bytes
 .../487322/images/html_487322_3bc603eb.png         | Bin 0 -> 27588 bytes
 .../487322/images/html_487322_3d59e52c.png         | Bin 0 -> 4338 bytes
 .../487322/images/html_487322_3e65e197.png         | Bin 0 -> 70935 bytes
 .../487322/images/html_487322_418241b4.png         | Bin 0 -> 50749 bytes
 .../487322/images/html_487322_42f54eae.png         | Bin 0 -> 4776 bytes
 .../487322/images/html_487322_44b1ed13.png         | Bin 0 -> 4789 bytes
 .../487322/images/html_487322_47460af2.png         | Bin 0 -> 51984 bytes
 .../487322/images/html_487322_488e5341.png         | Bin 0 -> 73820 bytes
 .../487322/images/html_487322_48cebb09.jpg         | Bin 0 -> 23763 bytes
 .../487322/images/html_487322_4bc1ed6c.png         | Bin 0 -> 3945 bytes
 .../487322/images/html_487322_4c2e16b9.png         | Bin 0 -> 4268 bytes
 .../487322/images/html_487322_4cea4676.png         | Bin 0 -> 71410 bytes
 .../487322/images/html_487322_4d623340.jpg         | Bin 0 -> 607 bytes
 .../487322/images/html_487322_4e1d001a.png         | Bin 0 -> 292842 bytes
 .../487322/images/html_487322_4f92fb3a.png         | Bin 0 -> 1289 bytes
 .../487322/images/html_487322_528d1438.png         | Bin 0 -> 70247 bytes
 .../487322/images/html_487322_5394ba93.png         | Bin 0 -> 73718 bytes
 .../487322/images/html_487322_55771615.png         | Bin 0 -> 69945 bytes
 .../487322/images/html_487322_59b768a6.png         | Bin 0 -> 238940 bytes
 .../487322/images/html_487322_5ae76bc5.png         | Bin 0 -> 70641 bytes
 .../487322/images/html_487322_5bef95af.png         | Bin 0 -> 275667 bytes
 .../487322/images/html_487322_5c6ee65e.png         | Bin 0 -> 186755 bytes
 .../487322/images/html_487322_5cb0b96f.png         | Bin 0 -> 64245 bytes
 .../487322/images/html_487322_5d3b5ecc.png         | Bin 0 -> 58635 bytes
 .../487322/images/html_487322_5ffce63d.png         | Bin 0 -> 29662 bytes
 .../487322/images/html_487322_604b2878.png         | Bin 0 -> 4430 bytes
 .../487322/images/html_487322_61823d87.png         | Bin 0 -> 4789 bytes
 .../487322/images/html_487322_62a1e327.png         | Bin 0 -> 25925 bytes
 .../487322/images/html_487322_686eb871.png         | Bin 0 -> 4619 bytes
 .../487322/images/html_487322_68dcfa1b.jpg         | Bin 0 -> 6526 bytes
 .../487322/images/html_487322_6b87f7ee.jpg         | Bin 0 -> 54371 bytes
 .../487322/images/html_487322_6e8549dc.jpg         | Bin 0 -> 16453 bytes
 .../487322/images/html_487322_6eee1a17.png         | Bin 0 -> 242345 bytes
 .../487322/images/html_487322_6f50ee37.png         | Bin 0 -> 209311 bytes
 .../487322/images/html_487322_6feb481d.jpg         | Bin 0 -> 18141 bytes
 .../487322/images/html_487322_71cdc738.png         | Bin 0 -> 4870 bytes
 .../487322/images/html_487322_76d1f308.png         | Bin 0 -> 1289 bytes
 .../487322/images/html_487322_76d80f06.png         | Bin 0 -> 73718 bytes
 .../487322/images/html_487322_770c7cbb.png         | Bin 0 -> 4338 bytes
 .../487322/images/html_487322_7862aee3.png         | Bin 0 -> 3526 bytes
 .../487322/images/html_487322_790bf7ed.png         | Bin 0 -> 2313 bytes
 .../487322/images/html_487322_79d43db3.jpg         | Bin 0 -> 607 bytes
 .../487322/images/html_487322_7d7de4c8.png         | Bin 0 -> 4046 bytes
 .../487322/images/html_487322_7ebfeb57.jpg         | Bin 0 -> 14613 bytes
 .../487322/images/html_487322_7f8447a4.png         | Bin 0 -> 103205 bytes
 .../487322/images/html_487322_80105745.png         | Bin 0 -> 70139 bytes
 .../487322/images/html_487322_866b4fbd.png         | Bin 0 -> 49105 bytes
 .../487322/images/html_487322_871c75ee.jpg         | Bin 0 -> 16147 bytes
 .../487322/images/html_487322_8b5f79f9.png         | Bin 0 -> 275667 bytes
 .../487322/images/html_487322_9101343e.jpg         | Bin 0 -> 1401 bytes
 .../487322/images/html_487322_918f4b48.jpg         | Bin 0 -> 14713 bytes
 .../487322/images/html_487322_91cdf91f.png         | Bin 0 -> 167777 bytes
 .../487322/images/html_487322_9225ae60.png         | Bin 0 -> 4006 bytes
 .../487322/images/html_487322_9488bcef.png         | Bin 0 -> 4553 bytes
 .../487322/images/html_487322_9595ddad.png         | Bin 0 -> 280044 bytes
 .../487322/images/html_487322_96fa68ad.png         | Bin 0 -> 47049 bytes
 .../487322/images/html_487322_975a0f98.jpg         | Bin 0 -> 14770 bytes
 .../487322/images/html_487322_97631ae0.png         | Bin 0 -> 4619 bytes
 .../487322/images/html_487322_997ec318.png         | Bin 0 -> 14380 bytes
 .../487322/images/html_487322_9a806f19.jpg         | Bin 0 -> 42392 bytes
 .../487322/images/html_487322_9dc341dc.png         | Bin 0 -> 314803 bytes
 .../487322/images/html_487322_9e7ec290.png         | Bin 0 -> 281315 bytes
 .../487322/images/html_487322_9eab7d17.jpg         | Bin 0 -> 1401 bytes
 .../487322/images/html_487322_9ef86315.png         | Bin 0 -> 1341 bytes
 .../487322/images/html_487322_a02a8727.jpg         | Bin 0 -> 49946 bytes
 .../487322/images/html_487322_a69d83c3.png         | Bin 0 -> 14148 bytes
 .../487322/images/html_487322_a8544941.png         | Bin 0 -> 3933 bytes
 .../487322/images/html_487322_aaa1bbb3.png         | Bin 0 -> 2535 bytes
 .../487322/images/html_487322_ab10cc85.png         | Bin 0 -> 52195 bytes
 .../487322/images/html_487322_ab11843a.jpg         | Bin 0 -> 12943 bytes
 .../487322/images/html_487322_ab562408.png         | Bin 0 -> 106645 bytes
 .../487322/images/html_487322_ac3033af.png         | Bin 0 -> 14380 bytes
 .../487322/images/html_487322_ae57f447.jpg         | Bin 0 -> 16453 bytes
 .../487322/images/html_487322_af84bc0b.png         | Bin 0 -> 87553 bytes
 .../487322/images/html_487322_b013d1d4.png         | Bin 0 -> 4995 bytes
 .../487322/images/html_487322_b0a1f9bc.jpg         | Bin 0 -> 1540 bytes
 .../487322/images/html_487322_b0c87cc7.png         | Bin 0 -> 314803 bytes
 .../487322/images/html_487322_b9b96f9f.jpg         | Bin 0 -> 12573 bytes
 .../487322/images/html_487322_b9efcb59.jpg         | Bin 0 -> 18147 bytes
 .../487322/images/html_487322_ba4f4f9d.png         | Bin 0 -> 293033 bytes
 .../487322/images/html_487322_bdd2e52a.jpg         | Bin 0 -> 1256 bytes
 .../487322/images/html_487322_bfc2c26c.png         | Bin 0 -> 2380 bytes
 .../487322/images/html_487322_c09d95ba.png         | Bin 0 -> 353523 bytes
 .../487322/images/html_487322_c0f9a2f2.jpg         | Bin 0 -> 17782 bytes
 .../487322/images/html_487322_c25773a9.png         | Bin 0 -> 77792 bytes
 .../487322/images/html_487322_c259bb25.png         | Bin 0 -> 1311 bytes
 .../487322/images/html_487322_c8a2e2bc.png         | Bin 0 -> 104947 bytes
 .../487322/images/html_487322_c983fdb8.png         | Bin 0 -> 261383 bytes
 .../487322/images/html_487322_d0b2efd8.jpg         | Bin 0 -> 6526 bytes
 .../487322/images/html_487322_d15142a1.png         | Bin 0 -> 215582 bytes
 .../487322/images/html_487322_d22cf316.png         | Bin 0 -> 29825 bytes
 .../487322/images/html_487322_d2c62f66.png         | Bin 0 -> 187796 bytes
 .../487322/images/html_487322_d3d2587e.jpg         | Bin 0 -> 42392 bytes
 .../487322/images/html_487322_d98cba03.png         | Bin 0 -> 69948 bytes
 .../487322/images/html_487322_d9a3ff41.jpg         | Bin 0 -> 1401 bytes
 .../487322/images/html_487322_dae7f9d6.png         | Bin 0 -> 2017 bytes
 .../487322/images/html_487322_de7b7a80.jpg         | Bin 0 -> 20389 bytes
 .../487322/images/html_487322_e01d68bb.png         | Bin 0 -> 281315 bytes
 .../487322/images/html_487322_e0d6a7b8.jpg         | Bin 0 -> 1253 bytes
 .../487322/images/html_487322_e3327249.png         | Bin 0 -> 4178 bytes
 .../487322/images/html_487322_e4680d92.png         | Bin 0 -> 4338 bytes
 .../487322/images/html_487322_e4c98c7f.png         | Bin 0 -> 28205 bytes
 .../487322/images/html_487322_e62dc97e.jpg         | Bin 0 -> 18147 bytes
 .../487322/images/html_487322_e92200a9.jpg         | Bin 0 -> 12573 bytes
 .../487322/images/html_487322_ec22682e.png         | Bin 0 -> 98282 bytes
 .../487322/images/html_487322_ed76d2ed.png         | Bin 0 -> 73718 bytes
 .../487322/images/html_487322_f024f8cc.jpg         | Bin 0 -> 49607 bytes
 .../487322/images/html_487322_f13fa8de.png         | Bin 0 -> 255848 bytes
 .../487322/images/html_487322_f88111b2.jpg         | Bin 0 -> 60347 bytes
 .../487322/images/html_487322_f8bbc767.png         | Bin 0 -> 62656 bytes
 .../487322/images/html_487322_fc614433.jpg         | Bin 0 -> 1740 bytes
 .../487322/images/html_487322_fcb534ab.png         | Bin 0 -> 5357 bytes
 .../487322/images/html_487322_fdcffdfe.png         | Bin 0 -> 77792 bytes
 .../7527803282/images/btf_7527803282_10b562f9.jpg  | Bin 0 -> 1201736 bytes
 .../7527803282/images/btf_7527803282_baf2cc73.jpg  | Bin 0 -> 51844 bytes
 .../7527803282/images/html_7527803282_0f697911.jpg | Bin 0 -> 77161 bytes
 .../7527803282/images/html_7527803282_12da9fbd.jpg | Bin 0 -> 54992 bytes
 .../7527803282/images/html_7527803282_15259ded.png | Bin 0 -> 4546 bytes
 .../7527803282/images/html_7527803282_1b2301d3.jpg | Bin 0 -> 30080 bytes
 .../7527803282/images/html_7527803282_1d156011.jpg | Bin 0 -> 24992 bytes
 .../7527803282/images/html_7527803282_240947eb.jpg | Bin 0 -> 12291 bytes
 .../7527803282/images/html_7527803282_26e6ca48.jpg | Bin 0 -> 59306 bytes
 .../7527803282/images/html_7527803282_29281e77.png | Bin 0 -> 221785 bytes
 .../7527803282/images/html_7527803282_2b988ddd.jpg | Bin 0 -> 1226 bytes
 .../7527803282/images/html_7527803282_2c1554e9.jpg | Bin 0 -> 10069 bytes
 .../7527803282/images/html_7527803282_2dc9fff1.jpg | Bin 0 -> 27089 bytes
 .../7527803282/images/html_7527803282_2f451c25.png | Bin 0 -> 63442 bytes
 .../7527803282/images/html_7527803282_31a96c03.jpg | Bin 0 -> 43140 bytes
 .../7527803282/images/html_7527803282_32c16c14.jpg | Bin 0 -> 34144 bytes
 .../7527803282/images/html_7527803282_33ea04d5.jpg | Bin 0 -> 39560 bytes
 .../7527803282/images/html_7527803282_344693e9.png | Bin 0 -> 221425 bytes
 .../7527803282/images/html_7527803282_34475ab7.jpg | Bin 0 -> 1014 bytes
 .../7527803282/images/html_7527803282_3826ab63.png | Bin 0 -> 203498 bytes
 .../7527803282/images/html_7527803282_39f8b93e.jpg | Bin 0 -> 8833 bytes
 .../7527803282/images/html_7527803282_3a016065.png | Bin 0 -> 71988 bytes
 .../7527803282/images/html_7527803282_3c7dd35f.jpg | Bin 0 -> 14438 bytes
 .../7527803282/images/html_7527803282_401def54.jpg | Bin 0 -> 25348 bytes
 .../7527803282/images/html_7527803282_404dda5a.jpg | Bin 0 -> 9637 bytes
 .../7527803282/images/html_7527803282_49a2abd0.jpg | Bin 0 -> 10918 bytes
 .../7527803282/images/html_7527803282_4e5f20a2.jpg | Bin 0 -> 1117 bytes
 .../7527803282/images/html_7527803282_5145f261.png | Bin 0 -> 60318 bytes
 .../7527803282/images/html_7527803282_554289e3.png | Bin 0 -> 4223 bytes
 .../7527803282/images/html_7527803282_5615b213.png | Bin 0 -> 4181 bytes
 .../7527803282/images/html_7527803282_5f47533f.jpg | Bin 0 -> 9637 bytes
 .../7527803282/images/html_7527803282_643b9276.jpg | Bin 0 -> 21187 bytes
 .../7527803282/images/html_7527803282_68eb5bdf.jpg | Bin 0 -> 20857 bytes
 .../7527803282/images/html_7527803282_69fade42.jpg | Bin 0 -> 1831 bytes
 .../7527803282/images/html_7527803282_6e0e0191.jpg | Bin 0 -> 1317 bytes
 .../7527803282/images/html_7527803282_6e272ff5.jpg | Bin 0 -> 33969 bytes
 .../7527803282/images/html_7527803282_6eb1386f.jpg | Bin 0 -> 17881 bytes
 .../7527803282/images/html_7527803282_75e60ef6.jpg | Bin 0 -> 1181 bytes
 .../7527803282/images/html_7527803282_7dcf2303.jpg | Bin 0 -> 49227 bytes
 .../7527803282/images/html_7527803282_80206709.png | Bin 0 -> 4552 bytes
 .../7527803282/images/html_7527803282_8357c171.jpg | Bin 0 -> 1540 bytes
 .../7527803282/images/html_7527803282_83ea86d7.png | Bin 0 -> 211482 bytes
 .../7527803282/images/html_7527803282_87dd0404.jpg | Bin 0 -> 13221 bytes
 .../7527803282/images/html_7527803282_8bc841c8.jpg | Bin 0 -> 9003 bytes
 .../7527803282/images/html_7527803282_92b28807.jpg | Bin 0 -> 62819 bytes
 .../7527803282/images/html_7527803282_957ed33f.jpg | Bin 0 -> 1415 bytes
 .../7527803282/images/html_7527803282_96fac706.jpg | Bin 0 -> 47283 bytes
 .../7527803282/images/html_7527803282_976fb8eb.jpg | Bin 0 -> 9259 bytes
 .../7527803282/images/html_7527803282_9b6e0345.jpg | Bin 0 -> 17881 bytes
 .../7527803282/images/html_7527803282_9c04a35a.jpg | Bin 0 -> 11990 bytes
 .../7527803282/images/html_7527803282_9c6f13cc.png | Bin 0 -> 4182 bytes
 .../7527803282/images/html_7527803282_9c9c5bbd.jpg | Bin 0 -> 40343 bytes
 .../7527803282/images/html_7527803282_9cd3b687.jpg | Bin 0 -> 40203 bytes
 .../7527803282/images/html_7527803282_9f00f760.jpg | Bin 0 -> 15946 bytes
 .../7527803282/images/html_7527803282_a08f4613.jpg | Bin 0 -> 9716 bytes
 .../7527803282/images/html_7527803282_a202154c.jpg | Bin 0 -> 4824 bytes
 .../7527803282/images/html_7527803282_a31ba760.png | Bin 0 -> 58845 bytes
 .../7527803282/images/html_7527803282_a4ad29c6.jpg | Bin 0 -> 971 bytes
 .../7527803282/images/html_7527803282_a6db4ed4.jpg | Bin 0 -> 1335 bytes
 .../7527803282/images/html_7527803282_a76e242d.jpg | Bin 0 -> 28012 bytes
 .../7527803282/images/html_7527803282_a94eaeb3.jpg | Bin 0 -> 19009 bytes
 .../7527803282/images/html_7527803282_ab592f79.jpg | Bin 0 -> 17118 bytes
 .../7527803282/images/html_7527803282_b04df6bb.jpg | Bin 0 -> 12853 bytes
 .../7527803282/images/html_7527803282_b26c3102.jpg | Bin 0 -> 7684 bytes
 .../7527803282/images/html_7527803282_b4d81b51.jpg | Bin 0 -> 40109 bytes
 .../7527803282/images/html_7527803282_b5a2ce61.jpg | Bin 0 -> 1670 bytes
 .../7527803282/images/html_7527803282_ba0e5d0c.png | Bin 0 -> 4178 bytes
 .../7527803282/images/html_7527803282_bc3703ae.jpg | Bin 0 -> 9750 bytes
 .../7527803282/images/html_7527803282_bc5764eb.png | Bin 0 -> 71988 bytes
 .../7527803282/images/html_7527803282_bd7a0b8a.jpg | Bin 0 -> 1448 bytes
 .../7527803282/images/html_7527803282_c5f97fef.png | Bin 0 -> 262271 bytes
 .../7527803282/images/html_7527803282_cdd98e30.jpg | Bin 0 -> 8833 bytes
 .../7527803282/images/html_7527803282_cfd57879.jpg | Bin 0 -> 34953 bytes
 .../7527803282/images/html_7527803282_d02dd398.png | Bin 0 -> 58693 bytes
 .../7527803282/images/html_7527803282_d1771fd3.png | Bin 0 -> 4546 bytes
 .../7527803282/images/html_7527803282_d7432fe4.jpg | Bin 0 -> 23388 bytes
 .../7527803282/images/html_7527803282_da58c57b.jpg | Bin 0 -> 14813 bytes
 .../7527803282/images/html_7527803282_dafe1ee8.jpg | Bin 0 -> 1304 bytes
 .../7527803282/images/html_7527803282_db339077.jpg | Bin 0 -> 13221 bytes
 .../7527803282/images/html_7527803282_dd10839b.jpg | Bin 0 -> 29650 bytes
 .../7527803282/images/html_7527803282_df8dbb8c.png | Bin 0 -> 58776 bytes
 .../7527803282/images/html_7527803282_df999ab8.png | Bin 0 -> 4552 bytes
 .../7527803282/images/html_7527803282_e0370ba0.jpg | Bin 0 -> 1540 bytes
 .../7527803282/images/html_7527803282_e1a1a42b.jpg | Bin 0 -> 11661 bytes
 .../7527803282/images/html_7527803282_e4f8d093.jpg | Bin 0 -> 13179 bytes
 .../7527803282/images/html_7527803282_e6d52758.jpg | Bin 0 -> 37050 bytes
 .../7527803282/images/html_7527803282_ed1048b7.jpg | Bin 0 -> 7585 bytes
 .../7527803282/images/html_7527803282_ed7c58b7.png | Bin 0 -> 63442 bytes
 .../7527803282/images/html_7527803282_f101234c.jpg | Bin 0 -> 20857 bytes
 .../7527803282/images/html_7527803282_f6b1d9c2.jpg | Bin 0 -> 11116 bytes
 .../7527803282/images/html_7527803282_f871b84f.jpg | Bin 0 -> 31352 bytes
 .../7527803282/images/html_7527803282_fc9e3233.jpg | Bin 0 -> 11153 bytes
 .../7527803282/images/html_7527803282_fcbae3ea.png | Bin 0 -> 221071 bytes
 .../7527803282/images/html_7527803282_fd8b2592.jpg | Bin 0 -> 7652 bytes
 .../7958974/images/btf_7958974_ad6b26b9.jpg        | Bin 0 -> 1045478 bytes
 .../7958974/images/html_7958974_02bd5f94.jpg       | Bin 0 -> 1545 bytes
 .../7958974/images/html_7958974_144517f0.jpg       | Bin 0 -> 70611 bytes
 .../7958974/images/html_7958974_1ab0619d.jpg       | Bin 0 -> 24873 bytes
 .../7958974/images/html_7958974_37ddc551.jpg       | Bin 0 -> 75273 bytes
 .../7958974/images/html_7958974_4d1fa829.png       | Bin 0 -> 2776 bytes
 .../7958974/images/html_7958974_506dea26.jpg       | Bin 0 -> 11856 bytes
 .../7958974/images/html_7958974_580ba2c9.jpg       | Bin 0 -> 36342 bytes
 .../7958974/images/html_7958974_59c668b3.jpg       | Bin 0 -> 45375 bytes
 .../7958974/images/html_7958974_72ddf9b9.jpg       | Bin 0 -> 17510 bytes
 .../7958974/images/html_7958974_7a644f15.jpg       | Bin 0 -> 21066 bytes
 .../7958974/images/html_7958974_7b0d3244.jpg       | Bin 0 -> 8726 bytes
 .../7958974/images/html_7958974_87bcde57.jpg       | Bin 0 -> 59655 bytes
 .../7958974/images/html_7958974_8ae48100.png       | Bin 0 -> 4061 bytes
 .../7958974/images/html_7958974_8e1b915f.png       | Bin 0 -> 176405 bytes
 .../7958974/images/html_7958974_8e1fbf1b.jpg       | Bin 0 -> 66170 bytes
 .../7958974/images/html_7958974_94ebf37b.jpg       | Bin 0 -> 43910 bytes
 .../7958974/images/html_7958974_9dd92581.jpg       | Bin 0 -> 29487 bytes
 .../7958974/images/html_7958974_a1eab505.png       | Bin 0 -> 43029 bytes
 .../7958974/images/html_7958974_ae6336cc.jpg       | Bin 0 -> 42163 bytes
 .../7958974/images/html_7958974_b071cbce.jpg       | Bin 0 -> 26987 bytes
 .../7958974/images/html_7958974_c10f04f4.jpg       | Bin 0 -> 901 bytes
 .../7958974/images/html_7958974_c3c8c27f.jpg       | Bin 0 -> 27356 bytes
 .../7958974/images/html_7958974_d6fec775.jpg       | Bin 0 -> 22825 bytes
 .../7958974/images/html_7958974_e3e06590.jpg       | Bin 0 -> 1265 bytes
 .../7958974/images/html_7958974_e4372ada.jpg       | Bin 0 -> 88791 bytes
 .../7958974/images/html_7958974_e9bfa058.png       | Bin 0 -> 62667 bytes
 .../7958974/images/html_7958974_ea0e490d.jpg       | Bin 0 -> 23865 bytes
 .../7958974/images/html_7958974_ec7ff2ba.jpg       | Bin 0 -> 2012 bytes
 .../7958974/images/html_7958974_ee6f3c1b.jpg       | Bin 0 -> 38377 bytes
 .../7958974/images/html_7958974_f240b7a3.jpg       | Bin 0 -> 79934 bytes
 .../7958974/images/html_7958974_fad6d217.jpg       | Bin 0 -> 1546 bytes
 .../7958974/images/html_7958974_fd25380c.png       | Bin 0 -> 238912 bytes
 .../8289731246/images/btf_8289731246_8a109955.jpg  | Bin 0 -> 2527573 bytes
 .../8289731246/images/btf_8289731246_b75c2672.jpg  | Bin 0 -> 1974233 bytes
 .../8289731246/images/html_8289731246_0065c33f.png | Bin 0 -> 4328 bytes
 .../8289731246/images/html_8289731246_048220f7.png | Bin 0 -> 64601 bytes
 .../8289731246/images/html_8289731246_0caad7b0.jpg | Bin 0 -> 25741 bytes
 .../8289731246/images/html_8289731246_1b5786f5.jpg | Bin 0 -> 2273 bytes
 .../8289731246/images/html_8289731246_2419aaa9.png | Bin 0 -> 5649 bytes
 .../8289731246/images/html_8289731246_2584d011.png | Bin 0 -> 100468 bytes
 .../8289731246/images/html_8289731246_47552f96.png | Bin 0 -> 97448 bytes
 .../8289731246/images/html_8289731246_4cd9bb7e.jpg | Bin 0 -> 2079 bytes
 .../8289731246/images/html_8289731246_5bbf6f72.jpg | Bin 0 -> 22576 bytes
 .../8289731246/images/html_8289731246_7eeb34bb.png | Bin 0 -> 99786 bytes
 .../8289731246/images/html_8289731246_8a330918.jpg | Bin 0 -> 16352 bytes
 .../8289731246/images/html_8289731246_a32a9854.jpg | Bin 0 -> 19747 bytes
 .../8289731246/images/html_8289731246_a70ad537.png | Bin 0 -> 5421 bytes
 .../8289731246/images/html_8289731246_a777ee23.jpg | Bin 0 -> 2336 bytes
 .../8289731246/images/html_8289731246_acddf1c2.png | Bin 0 -> 5390 bytes
 .../8289731246/images/html_8289731246_af1f2865.jpg | Bin 0 -> 24576 bytes
 .../8289731246/images/html_8289731246_c8b81d66.png | Bin 0 -> 1930 bytes
 .../8289731246/images/html_8289731246_c91ba264.jpg | Bin 0 -> 84975 bytes
 .../8289731246/images/html_8289731246_ccf18745.jpg | Bin 0 -> 1863 bytes
 .../8289731246/images/html_8289731246_ce73a4a4.jpg | Bin 0 -> 73514 bytes
 .../8289731246/images/html_8289731246_d8f99820.png | Bin 0 -> 24357 bytes
 .../8289731246/images/html_8289731246_e6f214fe.jpg | Bin 0 -> 63121 bytes
 .../8289731246/images/html_8289731246_f1d83688.jpg | Bin 0 -> 2398 bytes
 .../8289731246/images/html_8289731246_f2af0433.jpg | Bin 0 -> 80367 bytes
 .../86564/images/btf_86564_0fafa053.png            | Bin 0 -> 95929 bytes
 .../86564/images/btf_86564_253ff7bf.jpg            | Bin 0 -> 41139 bytes
 .../86564/images/btf_86564_4402840e.png            | Bin 0 -> 62069 bytes
 .../86564/images/btf_86564_5b829161.jpg            | Bin 0 -> 1008376 bytes
 .../86564/images/btf_86564_96b133c4.png            | Bin 0 -> 87625 bytes
 .../86564/images/btf_86564_f9d67ad4.png            | Bin 0 -> 41529 bytes
 .../86564/images/html_86564_039b0ac8.jpg           | Bin 0 -> 41161 bytes
 .../86564/images/html_86564_04955d6e.jpg           | Bin 0 -> 12792 bytes
 .../86564/images/html_86564_05dfc3d3.jpg           | Bin 0 -> 58601 bytes
 .../86564/images/html_86564_069c12fe.jpg           | Bin 0 -> 58601 bytes
 .../86564/images/html_86564_09dff07a.jpg           | Bin 0 -> 15064 bytes
 .../86564/images/html_86564_1358cb9e.jpg           | Bin 0 -> 20702 bytes
 .../86564/images/html_86564_164e8dd9.jpg           | Bin 0 -> 2026 bytes
 .../86564/images/html_86564_1826e767.jpg           | Bin 0 -> 12792 bytes
 .../86564/images/html_86564_195b1651.jpg           | Bin 0 -> 12792 bytes
 .../86564/images/html_86564_1d25ca96.jpg           | Bin 0 -> 24163 bytes
 .../86564/images/html_86564_1e5e754d.jpg           | Bin 0 -> 34177 bytes
 .../86564/images/html_86564_20ed79d8.jpg           | Bin 0 -> 999 bytes
 .../86564/images/html_86564_2235513c.jpg           | Bin 0 -> 999 bytes
 .../86564/images/html_86564_2336dce9.jpg           | Bin 0 -> 1425 bytes
 .../86564/images/html_86564_2de8ced7.jpg           | Bin 0 -> 41161 bytes
 .../86564/images/html_86564_30a88b4d.jpg           | Bin 0 -> 34177 bytes
 .../86564/images/html_86564_350e54ab.jpg           | Bin 0 -> 12792 bytes
 .../86564/images/html_86564_38371b13.jpg           | Bin 0 -> 17762 bytes
 .../86564/images/html_86564_42f22c60.jpg           | Bin 0 -> 17762 bytes
 .../86564/images/html_86564_437973e1.jpg           | Bin 0 -> 17762 bytes
 .../86564/images/html_86564_468ccd2a.jpg           | Bin 0 -> 15657 bytes
 .../86564/images/html_86564_4aa96c72.jpg           | Bin 0 -> 1468 bytes
 .../86564/images/html_86564_4bcfa0ce.jpg           | Bin 0 -> 24163 bytes
 .../86564/images/html_86564_4c46faca.jpg           | Bin 0 -> 15657 bytes
 .../86564/images/html_86564_52acd5f7.jpg           | Bin 0 -> 24163 bytes
 .../86564/images/html_86564_550f901a.jpg           | Bin 0 -> 20702 bytes
 .../86564/images/html_86564_59d65380.jpg           | Bin 0 -> 2111 bytes
 .../86564/images/html_86564_5b047eff.jpg           | Bin 0 -> 78445 bytes
 .../86564/images/html_86564_5e0b39d4.jpg           | Bin 0 -> 15064 bytes
 .../86564/images/html_86564_63c83da3.jpg           | Bin 0 -> 999 bytes
 .../86564/images/html_86564_646fe5da.jpg           | Bin 0 -> 1425 bytes
 .../86564/images/html_86564_763df2df.jpg           | Bin 0 -> 41161 bytes
 .../86564/images/html_86564_77614e96.jpg           | Bin 0 -> 15657 bytes
 .../86564/images/html_86564_7e0030d8.jpg           | Bin 0 -> 1468 bytes
 .../86564/images/html_86564_804ea1d7.jpg           | Bin 0 -> 68893 bytes
 .../86564/images/html_86564_85959c65.jpg           | Bin 0 -> 58601 bytes
 .../86564/images/html_86564_87c48607.jpg           | Bin 0 -> 68893 bytes
 .../86564/images/html_86564_89c50b54.jpg           | Bin 0 -> 72244 bytes
 .../86564/images/html_86564_97e0110a.jpg           | Bin 0 -> 2111 bytes
 .../86564/images/html_86564_a04f21b4.jpg           | Bin 0 -> 2167 bytes
 .../86564/images/html_86564_a186fadd.jpg           | Bin 0 -> 78445 bytes
 .../86564/images/html_86564_ae601efd.jpg           | Bin 0 -> 41161 bytes
 .../86564/images/html_86564_b2eb2122.jpg           | Bin 0 -> 15064 bytes
 .../86564/images/html_86564_b5cf74d4.jpg           | Bin 0 -> 81029 bytes
 .../86564/images/html_86564_b6ec0dda.jpg           | Bin 0 -> 2111 bytes
 .../86564/images/html_86564_c1a092c1.jpg           | Bin 0 -> 999 bytes
 .../86564/images/html_86564_c5c4fa1b.jpg           | Bin 0 -> 999 bytes
 .../86564/images/html_86564_ce9d74fd.jpg           | Bin 0 -> 54684 bytes
 .../86564/images/html_86564_d0b05745.jpg           | Bin 0 -> 1425 bytes
 .../86564/images/html_86564_d2e11aa2.jpg           | Bin 0 -> 2167 bytes
 .../86564/images/html_86564_da593572.jpg           | Bin 0 -> 72244 bytes
 .../86564/images/html_86564_de10be88.jpg           | Bin 0 -> 999 bytes
 .../86564/images/html_86564_e325f09e.jpg           | Bin 0 -> 12792 bytes
 .../86564/images/html_86564_e475d7ae.jpg           | Bin 0 -> 12792 bytes
 .../86564/images/html_86564_e6a9873f.jpg           | Bin 0 -> 54684 bytes
 .../86564/images/html_86564_ea43a470.jpg           | Bin 0 -> 1468 bytes
 .../86564/images/html_86564_eabd0c59.jpg           | Bin 0 -> 34177 bytes
 .../86564/images/html_86564_ef8afa60.jpg           | Bin 0 -> 41161 bytes
 .../86564/images/html_86564_f25d88c6.jpg           | Bin 0 -> 2167 bytes
 .../86564/images/html_86564_fe5e5348.jpg           | Bin 0 -> 20702 bytes
 .../86564/images/html_86564_feb763e8.jpg           | Bin 0 -> 22028 bytes
 .../8826288636/images/btf_8826288636_1eaccbcb.png  | Bin 0 -> 745342 bytes
 .../8826288636/images/btf_8826288636_bc54740f.jpg  | Bin 0 -> 502999 bytes
 .../8826288636/images/html_8826288636_12bca94e.png | Bin 0 -> 64709 bytes
 .../8826288636/images/html_8826288636_14022d24.jpg | Bin 0 -> 57982 bytes
 .../8826288636/images/html_8826288636_16c4a544.jpg | Bin 0 -> 2185 bytes
 .../8826288636/images/html_8826288636_174f83d3.jpg | Bin 0 -> 2178 bytes
 .../8826288636/images/html_8826288636_1bc9c49c.jpg | Bin 0 -> 24188 bytes
 .../8826288636/images/html_8826288636_24427c53.jpg | Bin 0 -> 23537 bytes
 .../8826288636/images/html_8826288636_276aed76.jpg | Bin 0 -> 13669 bytes
 .../8826288636/images/html_8826288636_2801fa13.jpg | Bin 0 -> 14036 bytes
 .../8826288636/images/html_8826288636_2a2b6863.jpg | Bin 0 -> 10661 bytes
 .../8826288636/images/html_8826288636_2eda65b5.jpg | Bin 0 -> 58516 bytes
 .../8826288636/images/html_8826288636_2ffcf952.jpg | Bin 0 -> 11372 bytes
 .../8826288636/images/html_8826288636_39708fe6.jpg | Bin 0 -> 43334 bytes
 .../8826288636/images/html_8826288636_4d375b58.png | Bin 0 -> 38077 bytes
 .../8826288636/images/html_8826288636_4ed82994.jpg | Bin 0 -> 2286 bytes
 .../8826288636/images/html_8826288636_501a7d39.jpg | Bin 0 -> 82050 bytes
 .../8826288636/images/html_8826288636_5183ee72.jpg | Bin 0 -> 2298 bytes
 .../8826288636/images/html_8826288636_552b919f.jpg | Bin 0 -> 1550 bytes
 .../8826288636/images/html_8826288636_55549ce5.jpg | Bin 0 -> 1166 bytes
 .../8826288636/images/html_8826288636_58280288.png | Bin 0 -> 53015 bytes
 .../8826288636/images/html_8826288636_5b40e4b9.png | Bin 0 -> 2678 bytes
 .../8826288636/images/html_8826288636_5e6b0844.png | Bin 0 -> 4087 bytes
 .../8826288636/images/html_8826288636_5eab13cc.jpg | Bin 0 -> 22045 bytes
 .../8826288636/images/html_8826288636_60c4d7cb.jpg | Bin 0 -> 21187 bytes
 .../8826288636/images/html_8826288636_63d94b3b.jpg | Bin 0 -> 24586 bytes
 .../8826288636/images/html_8826288636_6f9c6f49.png | Bin 0 -> 120642 bytes
 .../8826288636/images/html_8826288636_7b912cb1.jpg | Bin 0 -> 76647 bytes
 .../8826288636/images/html_8826288636_7ed7f6ee.png | Bin 0 -> 3457 bytes
 .../8826288636/images/html_8826288636_7efb20fc.jpg | Bin 0 -> 45219 bytes
 .../8826288636/images/html_8826288636_8433f6a7.png | Bin 0 -> 61319 bytes
 .../8826288636/images/html_8826288636_89cb0a2e.jpg | Bin 0 -> 1296 bytes
 .../8826288636/images/html_8826288636_9ee267f1.jpg | Bin 0 -> 2195 bytes
 .../8826288636/images/html_8826288636_a04c14df.jpg | Bin 0 -> 11372 bytes
 .../8826288636/images/html_8826288636_a15b01d3.jpg | Bin 0 -> 24586 bytes
 .../8826288636/images/html_8826288636_a31ad40f.jpg | Bin 0 -> 24443 bytes
 .../8826288636/images/html_8826288636_bc7c55c9.jpg | Bin 0 -> 77737 bytes
 .../8826288636/images/html_8826288636_bfb02770.jpg | Bin 0 -> 2371 bytes
 .../8826288636/images/html_8826288636_bfe3ee38.jpg | Bin 0 -> 23014 bytes
 .../8826288636/images/html_8826288636_cae7af1e.png | Bin 0 -> 6846 bytes
 .../8826288636/images/html_8826288636_d80d5584.jpg | Bin 0 -> 21921 bytes
 .../8826288636/images/html_8826288636_ddecf7c7.png | Bin 0 -> 53015 bytes
 .../8826288636/images/html_8826288636_e0c1eca0.jpg | Bin 0 -> 76397 bytes
 .../8826288636/images/html_8826288636_e6a62e14.png | Bin 0 -> 202746 bytes
 .../8826288636/images/html_8826288636_e7dd38b6.png | Bin 0 -> 228015 bytes
 .../8826288636/images/html_8826288636_eb850c68.jpg | Bin 0 -> 23498 bytes
 .../8826288636/images/html_8826288636_ec27116a.jpg | Bin 0 -> 84886 bytes
 .../8826288636/images/html_8826288636_fca4135b.png | Bin 0 -> 3457 bytes
 .../96571/images/btf_96571_3309d63c.jpg            | Bin 0 -> 704434 bytes
 .../96571/images/btf_96571_9202a3c2.png            | Bin 0 -> 419412 bytes
 .../96571/images/html_96571_00558a70.png           | Bin 0 -> 231092 bytes
 .../96571/images/html_96571_05573bef.png           | Bin 0 -> 221416 bytes
 .../96571/images/html_96571_0850ccb9.png           | Bin 0 -> 311385 bytes
 .../96571/images/html_96571_0b20316a.png           | Bin 0 -> 283646 bytes
 .../96571/images/html_96571_0c852b4e.png           | Bin 0 -> 311385 bytes
 .../96571/images/html_96571_0fe87ef1.jpg           | Bin 0 -> 18866 bytes
 .../96571/images/html_96571_12571c16.png           | Bin 0 -> 69616 bytes
 .../96571/images/html_96571_1687d2ba.png           | Bin 0 -> 4674 bytes
 .../96571/images/html_96571_1b7ca2e1.png           | Bin 0 -> 3843 bytes
 .../96571/images/html_96571_1e0b407f.png           | Bin 0 -> 5919 bytes
 .../96571/images/html_96571_233666b0.png           | Bin 0 -> 4646 bytes
 .../96571/images/html_96571_235d334c.jpg           | Bin 0 -> 53046 bytes
 .../96571/images/html_96571_2467343f.png           | Bin 0 -> 4646 bytes
 .../96571/images/html_96571_25bd236b.png           | Bin 0 -> 4202 bytes
 .../96571/images/html_96571_29fa621e.png           | Bin 0 -> 4674 bytes
 .../96571/images/html_96571_32412f4f.png           | Bin 0 -> 69616 bytes
 .../96571/images/html_96571_360375ad.png           | Bin 0 -> 5919 bytes
 .../96571/images/html_96571_39318125.png           | Bin 0 -> 76368 bytes
 .../96571/images/html_96571_3a126374.png           | Bin 0 -> 91795 bytes
 .../96571/images/html_96571_3a7dcd23.jpg           | Bin 0 -> 2175 bytes
 .../96571/images/html_96571_3b3d69cd.png           | Bin 0 -> 4202 bytes
 .../96571/images/html_96571_3cca5398.png           | Bin 0 -> 69616 bytes
 .../96571/images/html_96571_41c628a9.jpg           | Bin 0 -> 19526 bytes
 .../96571/images/html_96571_493db9b4.png           | Bin 0 -> 4202 bytes
 .../96571/images/html_96571_4d1d98a7.png           | Bin 0 -> 269069 bytes
 .../96571/images/html_96571_4e9d0042.png           | Bin 0 -> 4674 bytes
 .../96571/images/html_96571_53a35db7.png           | Bin 0 -> 4119 bytes
 .../96571/images/html_96571_57453ee8.png           | Bin 0 -> 4646 bytes
 .../96571/images/html_96571_5b284019.png           | Bin 0 -> 4202 bytes
 .../96571/images/html_96571_5d077334.jpg           | Bin 0 -> 32303 bytes
 .../96571/images/html_96571_5dbabe76.png           | Bin 0 -> 91795 bytes
 .../96571/images/html_96571_5fb14a36.jpg           | Bin 0 -> 8837 bytes
 .../96571/images/html_96571_66d269cf.png           | Bin 0 -> 60763 bytes
 .../96571/images/html_96571_677e06e2.png           | Bin 0 -> 76368 bytes
 .../96571/images/html_96571_6866bf08.png           | Bin 0 -> 344828 bytes
 .../96571/images/html_96571_70bdd0cb.png           | Bin 0 -> 76368 bytes
 .../96571/images/html_96571_8001f770.jpg           | Bin 0 -> 65409 bytes
 .../96571/images/html_96571_8087c838.png           | Bin 0 -> 63035 bytes
 .../96571/images/html_96571_84689801.png           | Bin 0 -> 60763 bytes
 .../96571/images/html_96571_946f4ca2.png           | Bin 0 -> 4646 bytes
 .../96571/images/html_96571_9736a988.png           | Bin 0 -> 60763 bytes
 .../96571/images/html_96571_9aa78f57.png           | Bin 0 -> 91795 bytes
 .../96571/images/html_96571_9af38678.png           | Bin 0 -> 231092 bytes
 .../96571/images/html_96571_a49ab0b7.png           | Bin 0 -> 4119 bytes
 .../96571/images/html_96571_ab2cbc4b.png           | Bin 0 -> 221416 bytes
 .../96571/images/html_96571_acdbc288.png           | Bin 0 -> 269069 bytes
 .../96571/images/html_96571_ad86526d.png           | Bin 0 -> 80509 bytes
 .../96571/images/html_96571_ade0bf5b.jpg           | Bin 0 -> 1799 bytes
 .../96571/images/html_96571_b1945f0a.png           | Bin 0 -> 344828 bytes
 .../96571/images/html_96571_b561df51.png           | Bin 0 -> 80509 bytes
 .../96571/images/html_96571_b5761b52.jpg           | Bin 0 -> 952 bytes
 .../96571/images/html_96571_b802eb3e.png           | Bin 0 -> 63035 bytes
 .../96571/images/html_96571_ba42847f.jpg           | Bin 0 -> 62396 bytes
 .../96571/images/html_96571_bc2671d6.png           | Bin 0 -> 69616 bytes
 .../96571/images/html_96571_be9486fd.png           | Bin 0 -> 63035 bytes
 .../96571/images/html_96571_c1750809.png           | Bin 0 -> 3843 bytes
 .../96571/images/html_96571_c362235e.png           | Bin 0 -> 80509 bytes
 .../96571/images/html_96571_c5b06b54.jpg           | Bin 0 -> 2052 bytes
 .../96571/images/html_96571_d3d570e8.png           | Bin 0 -> 269069 bytes
 .../96571/images/html_96571_d3e7619f.png           | Bin 0 -> 4119 bytes
 .../96571/images/html_96571_d82efe99.jpg           | Bin 0 -> 14715 bytes
 .../96571/images/html_96571_d8a3781b.png           | Bin 0 -> 221416 bytes
 .../96571/images/html_96571_d9da6e63.png           | Bin 0 -> 63035 bytes
 .../96571/images/html_96571_db44fa47.png           | Bin 0 -> 311385 bytes
 .../96571/images/html_96571_dc796122.png           | Bin 0 -> 3843 bytes
 .../96571/images/html_96571_dd450a11.png           | Bin 0 -> 5919 bytes
 .../96571/images/html_96571_e4444dbf.png           | Bin 0 -> 5919 bytes
 .../96571/images/html_96571_e5f5f3a6.jpg           | Bin 0 -> 2076 bytes
 .../96571/images/html_96571_ee146090.png           | Bin 0 -> 283646 bytes
 .../96571/images/html_96571_f5504b46.png           | Bin 0 -> 91795 bytes
 .../96571/images/html_96571_f92ad24e.jpg           | Bin 0 -> 19518 bytes
 .../96571/images/html_96571_f9f5ce9a.png           | Bin 0 -> 344828 bytes
 .../96571/images/html_96571_fc604744.png           | Bin 0 -> 4119 bytes
 .../96571/images/html_96571_fd717fce.png           | Bin 0 -> 80509 bytes
 urls.txt                                           | 261 +++++++++++++++++++++
 597 files changed, 261 insertions(+), 3 deletions(-)
45. data 디렉토리 - btf파일 ocr 결과 추가함
Date: 2025-10-29
Author: bae4147
Hash: d17c561
Changes
data/outputs_structured/1008978/ocrs_1008978.json  | 412 +++++++++++-
 .../185307349/ocrs_185307349.json                  | 265 +++++++-
 .../1912026433/ocrs_1912026433.json                | 274 +++++++-
 data/outputs_structured/487322/ocrs_487322.json    | 707 ++++++++++++++++++++-
 .../7527803282/ocrs_7527803282.json                | 230 ++++++-
 data/outputs_structured/7958974/ocrs_7958974.json  |  60 +-
 .../8289731246/ocrs_8289731246.json                | 224 ++++++-
 data/outputs_structured/86564/ocrs_86564.json      | 400 +++++++++++-
 .../8826288636/ocrs_8826288636.json                | 441 ++++++++++++-
 data/outputs_structured/96571/ocrs_96571.json      | 405 +++++++++++-
 10 files changed, 3292 insertions(+), 126 deletions(-)
46. preprocessing - ocr 코드 추가함. naver ocr
Date: 2025-10-29
Author: bae4147
Hash: 9fd7329
Changes
preprocessing/clova_ocr_batch.py | 429 +++++++++++++++++++++++++++++++++++++++
 1 file changed, 429 insertions(+)
47. rag 코드 수정 - product_*.json에서 상품 문의도 chunking하도록
Date: 2025-10-29
Author: bae4147
Hash: 58c678d
Changes
rag/rag_cache_products/8826288636/image_store.pkl  | Bin 29897 -> 0 bytes
 .../8826288636/ocr_store/index.faiss               | Bin 3117 -> 3117 bytes
 .../8826288636/ocr_store/index.pkl                 | Bin 654 -> 4988 bytes
 .../8826288636/product_store/index.faiss           | Bin 7725 -> 13869 bytes
 .../8826288636/product_store/index.pkl             | Bin 1228 -> 3149 bytes
 .../8826288636/review_store/index.pkl              | Bin 71077 -> 71077 bytes
 rag/rag_with_detail.py                             | 659 +++++++++++++++++++++
 rag/requirements.txt                               |   5 +-
 8 files changed, 663 insertions(+), 1 deletion(-)
48. Delete outputs_structured directory
Date: 2025-10-29
Author: Seunghyun Bae
Hash: 32769a0
Changes
.../1008978/image_manifest_1008978.json            |  64 -------
 outputs_structured/1008978/product_1008978.json    |  87 ---------
 .../185307349/image_manifest_185307349.json        |  16 --
 .../185307349/product_185307349.json               |  39 -----
 .../1912026433/image_manifest_1912026433.json      |  30 ----
 .../1912026433/product_1912026433.json             |  53 ------
 .../487322/image_manifest_487322.json              | 172 ------------------
 outputs_structured/487322/product_487322.json      | 195 ---------------------
 .../7527803282/image_manifest_7527803282.json      | 111 ------------
 .../7527803282/product_7527803282.json             | 134 --------------
 .../7958974/image_manifest_7958974.json            |  40 -----
 outputs_structured/7958974/product_7958974.json    |  63 -------
 .../8289731246/image_manifest_8289731246.json      |  41 -----
 .../8289731246/product_8289731246.json             |  64 -------
 outputs_structured/86564/image_manifest_86564.json |  76 --------
 outputs_structured/86564/product_86564.json        |  99 -----------
 .../8826288636/image_manifest_8826288636.json      |  61 -------
 .../8826288636/product_8826288636.json             |  84 ---------
 outputs_structured/96571/image_manifest_96571.json |  93 ----------
 outputs_structured/96571/product_96571.json        | 116 ------------
 20 files changed, 1638 deletions(-)
49. Delete outputs_inquiries directory
Date: 2025-10-29
Author: Seunghyun Bae
Hash: 760dd67
Changes
.../inquiries_8250433942_p1_1761113173275.json     | 144 ---------------------
 1 file changed, 144 deletions(-)
50. Delete .env
Date: 2025-10-29
Author: Seunghyun Bae
Hash: 725f87b
Changes
.env | 1 -
 1 file changed, 1 deletion(-)
51. Add Playwright agent for Coupang product interactions
Date: 2025-11-11
Author: Sung Geun An
Hash: d6250d1
Changes
agent/coupang_playwright_agent.py | 321 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 321 insertions(+)
52. Merge pull request #1 from ssunggun2/codex/implement-ai-agent-for-shopping-interactions
Date: 2025-11-11
Author: Sung Geun An
Hash: 79d5e87
53. Merge pull request #1 from ssunggun2/main
Date: 2025-11-11
Author: Sung Geun An
Hash: 9281458
54. Add scenario-aware pipeline for Coupang product interactions using Playwright. This module integrates crawling utilities and orchestrates data collection and dialog execution.
Date: 2025-11-11
Author: ssunggun2
Hash: eb57452
Changes
agent/coupang_scenario_pipeline.py | 367 +++++++++++++++++++++++++++++++++++++
 1 file changed, 367 insertions(+)
55. 시나리오 대로 구현한 코드 cli
Date: 2025-11-12
Author: bae4147
Hash: 5e2b735
Changes
agent/coupang_search_agent.py                      |  247 +
 agent/interactive_shopping_cli.py                  |  510 ++
 agent/llm_utils.py                                 |  175 +
 crawling/fetch_html.py                             |   58 +-
 .../html/response_8402175050.html                  |    9 +
 .../inquiries_8402175050_p1_1762938695399.json     |  155 +
 .../html/response_8402175050.html                  |    9 +
 .../inquiries_8402175050_p1_1762938867736.json     |  155 +
 .../quantity_info_8402175050_1762938868529.json    | 5817 ++++++++++++++++++++
 .../1008978/images/html_1008978_d81189f1.jpg       |  Bin 0 -> 66164 bytes
 .../185307349/images/html_185307349_57727e14.png   |  Bin 0 -> 282046 bytes
 .../185307349/images/html_185307349_a54eba06.jpg   |  Bin 0 -> 43258 bytes
 .../1912026433/images/html_1912026433_e9168d53.jpg |  Bin 0 -> 69367 bytes
 .../487322/images/html_487322_16e6a25c.jpg         |  Bin 0 -> 58971 bytes
 .../487322/images/html_487322_1e08f8cb.png         |  Bin 0 -> 50009 bytes
 .../487322/images/html_487322_6a66c558.png         |  Bin 0 -> 275667 bytes
 .../487322/images/html_487322_6f2c710f.jpg         |  Bin 0 -> 62131 bytes
 .../487322/images/html_487322_a11a8b10.png         |  Bin 0 -> 292842 bytes
 .../487322/images/html_487322_ab3aacf8.png         |  Bin 0 -> 109578 bytes
 .../487322/images/html_487322_b6580e76.jpg         |  Bin 0 -> 43358 bytes
 .../487322/images/html_487322_f7e534b6.jpg         |  Bin 0 -> 54447 bytes
 .../7527803282/images/html_7527803282_02129e5d.jpg |  Bin 0 -> 47283 bytes
 .../7527803282/images/html_7527803282_1fdae95f.jpg |  Bin 0 -> 40343 bytes
 .../7527803282/images/html_7527803282_25cd6739.jpg |  Bin 0 -> 43140 bytes
 .../7527803282/images/html_7527803282_30d583d3.jpg |  Bin 0 -> 58260 bytes
 .../7527803282/images/html_7527803282_c2f4c609.png |  Bin 0 -> 211482 bytes
 .../7527803282/images/html_7527803282_d02ed6f4.png |  Bin 0 -> 262271 bytes
 .../7527803282/images/html_7527803282_d07e7276.jpg |  Bin 0 -> 28815 bytes
 .../7958974/images/html_7958974_0447624a.jpg       |  Bin 0 -> 80487 bytes
 .../8289731246/images/html_8289731246_037e481f.png |  Bin 0 -> 436610 bytes
 .../8289731246/images/html_8289731246_5d087196.jpg |  Bin 0 -> 54971 bytes
 .../8289731246/images/html_8289731246_68d3dbbc.png |  Bin 0 -> 411331 bytes
 .../8289731246/images/html_8289731246_7d3ebffb.png |  Bin 0 -> 416431 bytes
 .../8289731246/images/html_8289731246_dc6d33fa.png |  Bin 0 -> 243793 bytes
 .../8289731246/images/html_8289731246_f743b6d2.png |  Bin 0 -> 82023 bytes
 .../86564/images/html_86564_4aa44c45.jpg           |  Bin 0 -> 68893 bytes
 .../86564/images/html_86564_5b601ed9.jpg           |  Bin 0 -> 78445 bytes
 .../86564/images/html_86564_60b8b958.jpg           |  Bin 0 -> 54684 bytes
 .../86564/images/html_86564_d59c0009.jpg           |  Bin 0 -> 72244 bytes
 .../86564/images/html_86564_ecce228b.jpg           |  Bin 0 -> 41161 bytes
 .../8826288636/images/html_8826288636_291e2a33.jpg |  Bin 0 -> 54842 bytes
 .../8826288636/images/html_8826288636_7c0e0781.jpg |  Bin 0 -> 58516 bytes
 .../8826288636/images/html_8826288636_c6ba2a61.jpg |  Bin 0 -> 66355 bytes
 .../8826288636/images/html_8826288636_d8b91a26.png |  Bin 0 -> 224437 bytes
 .../8826288636/images/html_8826288636_f4544cd4.png |  Bin 0 -> 202746 bytes
 .../96571/images/html_96571_2baba90d.png           |  Bin 0 -> 231092 bytes
 .../96571/images/html_96571_9a5fe554.png           |  Bin 0 -> 283646 bytes
 .../96571/images/html_96571_a1a70111.png           |  Bin 0 -> 269069 bytes
 .../96571/images/html_96571_b683fef0.jpg           |  Bin 0 -> 59419 bytes
 .../96571/images/html_96571_c995b5b6.png           |  Bin 0 -> 221416 bytes
 .../96571/images/html_96571_cddcc89a.png           |  Bin 0 -> 311385 bytes
 .../96571/images/html_96571_d2a36e53.png           |  Bin 0 -> 344828 bytes
 52 files changed, 7110 insertions(+), 25 deletions(-)
56. Enhance InteractiveShoppingCLI with cookie handling and structured data collection. Added support for JSON cookie formats, improved error handling during data collection, and introduced methods for fetching product HTML, reviews, inquiries, and quantity information.
Date: 2025-11-12
Author: ssunggun2
Hash: a92ae41
Changes
agent/interactive_shopping_cli.py | 279 +++++++++++++++++++++++++++++++++++---
 1 file changed, 262 insertions(+), 17 deletions(-)
57. Update .gitignore to exclude Python bytecode files, cache directories, and scenario output files.
Date: 2025-11-12
Author: ssunggun2
Hash: dc0ddf9
Changes
.gitignore | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
58. Refactor InteractiveShoppingCLI to implement Coupang search functionality using Playwright. Removed AI conversation features and integrated a new search agent for product retrieval, enhancing the overall structure and focus of the CLI.
Date: 2025-11-12
Author: ssunggun2
Hash: 3abdec1
Changes
agent/interactive_shopping_cli.py | 928 +++++++++-----------------------------
 1 file changed, 210 insertions(+), 718 deletions(-)
59. Revamp InteractiveShoppingCLI to incorporate AI-driven conversation features for enhanced user interaction. Introduced a state management system for conversation flow, integrated product search capabilities, and improved error handling. The CLI now supports dynamic user queries and structured data collection from Coupang, enriching the shopping experience.
Date: 2025-11-12
Author: ssunggun2
Hash: 88d86e2
Changes
agent/interactive_shopping_cli.py | 1041 +++++++++++++++++++++++++++++--------
 1 file changed, 833 insertions(+), 208 deletions(-)
60. Refactor InteractiveShoppingCLI to enhance artifact collection and browser session management. Introduced a dedicated ProductArtifactCollector for structured data retrieval, improved cookie handling, and streamlined browser initialization with Playwright. This update optimizes the CLI for better user interaction and data processing.
Date: 2025-11-12
Author: ssunggun2
Hash: 37ecbd4
Changes
agent/interactive_cli/__init__.py  |   7 +
 agent/interactive_cli/artifacts.py | 317 ++++++++++++++++++++++++
 agent/interactive_cli/browser.py   |  99 ++++++++
 agent/interactive_cli/cookies.py   |  85 +++++++
 agent/interactive_cli/state.py     |  28 +++
 agent/interactive_shopping_cli.py  | 485 +++----------------------------------
 6 files changed, 571 insertions(+), 450 deletions(-)
61. readme 추가함.
Date: 2025-11-13
Author: bae4147
Hash: 4b4eb7c
Changes
README.md | 331 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 330 insertions(+), 1 deletion(-)
62. Merge branch 'main' of https://github.com/5sudeng/DS_project
Date: 2025-11-13
Author: bae4147
Hash: 245f1b9
63. readme update
Date: 2025-11-13
Author: bae4147
Hash: d1f63a7
Changes
README.md | 8 --------
 1 file changed, 8 deletions(-)
64. Enhance InteractiveShoppingCLI and LLM utilities to incorporate artifact summary in user intent classification and query generation. Updated methods to include artifact context, improving the relevance of AI-driven responses and user interactions.
Date: 2025-11-13
Author: ssunggun2
Hash: 64900eb
Changes
agent/interactive_shopping_cli.py |  5 +++++
 agent/llm_utils.py                | 25 +++++++++++++++++++++++++
 2 files changed, 30 insertions(+)
65. Integrate logging into InteractiveShoppingCLI and ProductArtifactCollector for improved traceability. Added detailed log statements to track user interactions, product loading, and artifact collection processes, enhancing debugging and monitoring capabilities.
Date: 2025-11-13
Author: ssunggun2
Hash: a73450e
Changes
agent/interactive_cli/artifacts.py | 37 ++++++++++++++++++++++-
 agent/interactive_shopping_cli.py  | 42 +++++++++++++++++++++++++-
 agent/llm_utils.py                 | 60 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 137 insertions(+), 2 deletions(-)
66. Refactor CoupangProductAgent to enhance user query handling and data extraction. Removed outdated keyword extraction logic and integrated chunked dataset snippets for improved response accuracy. Added support for detail and specification sections in user queries, and streamlined the initialization of the ShoppingAssistantLLM for better performance.
Date: 2025-11-13
Author: ssunggun2
Hash: 1603aad
Changes
agent/coupang_playwright_agent.py | 368 +++++++++++++++++++++++++++-----------
 1 file changed, 262 insertions(+), 106 deletions(-)
67. Refactor CoupangProductAgent to enhance user query handling and data extraction. Removed keyword extraction logic and integrated chunked dataset snippets for improved response generation. Added support for detail and specification sections in user queries, and implemented a more robust intent classification mechanism in the demo function.
Date: 2025-11-13
Author: ssunggun2
Hash: c110464
Changes
agent/interactive_shopping_cli.py | 85 +++++++++++++++++++++++++++++----------
 1 file changed, 63 insertions(+), 22 deletions(-)
68. Enhance ShoppingAssistantLLM with debug print statements for user prompts and responses. Adjusted snippet limits and maximum length for improved context handling in response generation.
Date: 2025-11-13
Author: ssunggun2
Hash: 31f0138
Changes
agent/llm_utils.py | 7 +++++--
 1 file changed, 5 insertions(+), 2 deletions(-)
69. Add chunk dataset processing to ProductArtifactCollector for enhanced data handling. Implemented methods to build and persist chunked data from HTML, reviews, inquiries, and quantity files, improving artifact collection and summary generation.
Date: 2025-11-13
Author: ssunggun2
Hash: 4d682c3
Changes
agent/interactive_cli/artifacts.py | 115 +++++++++++++++++++++++++++++++++++++
 1 file changed, 115 insertions(+)
70. Merge pull request #2 from 5sudeng/ASG_dev
Date: 2025-11-13
Author: Sung Geun An
Hash: d7ed8fb
71. Update coupang_playwright_agent to launch Firefox browser and navigate to Coupang homepage. Added print statement for page title to enhance debugging and user feedback during demo runs.
Date: 2025-11-14
Author: ssunggun2
Hash: 2f7b3cd
Changes
agent/coupang_playwright_agent.py | 6 ++++--
 1 file changed, 4 insertions(+), 2 deletions(-)
72. Merge pull request #3 from 5sudeng/ASG_dev
Date: 2025-11-14
Author: Sung Geun An
Hash: 2b47761
73. Add CLOVA OCR integration and relevant snippet selection for improved product query handling
Date: 2025-11-19
Author: 5sudeng
Hash: c3926a9
Changes
README.md                          | 18 +++++++-
 agent/coupang_playwright_agent.py  | 32 ++++++++++++-
 agent/interactive_cli/artifacts.py | 94 +++++++++++++++++++++++++++++++++++++-
 agent/interactive_shopping_cli.py  | 23 ++++++++++
 agent/llm_utils.py                 | 51 +++++++++++++++++++++
 5 files changed, 214 insertions(+), 4 deletions(-)
74. Refactor README.md to enhance clarity and structure; updated feature descriptions and installation instructions.
Date: 2025-11-19
Author: 5sudeng
Hash: 0047523
Changes
README.md | 414 ++++++++++++++++++++++----------------------------------------
 1 file changed, 145 insertions(+), 269 deletions(-)
75. Merge pull request #4 from 5sudeng/main
Date: 2025-11-19
Author: Sung Geun An
Hash: 70886f2
76. Add .env to .gitignore to prevent sensitive environment variables from being tracked
Date: 2025-11-26
Author: 5sudeng
Hash: 84c85e1
Changes
.gitignore | 1 +
 1 file changed, 1 insertion(+)
77. Enhance artifact collection in CoupangScenarioPipeline and ProductArtifactCollector; added support for additional artifacts and improved directory handling.
Date: 2025-11-26
Author: 5sudeng
Hash: 1ed9203
Changes
agent/coupang_scenario_pipeline.py | 34 +++++++++++++++++++++++++++++++++-
 agent/interactive_cli/artifacts.py | 31 ++++++++++++++++++++++++++++++-
 2 files changed, 63 insertions(+), 2 deletions(-)
78. feat: Introduce API key support for LLM initialization and add project setup scripts and requirements.
Date: 2025-11-26
Author: ssunggun2
Hash: cb45b16
Changes
agent/coupang_playwright_agent.py |  4 +++-
 agent/interactive_shopping_cli.py |  2 ++
 requirements.txt                  | 17 +++++++++++++++++
 run_agent.sh                      | 14 ++++++++++++++
 4 files changed, 36 insertions(+), 1 deletion(-)
79. Merge pull request #5 from 5sudeng/main
Date: 2025-11-26
Author: Sung Geun An
Hash: 09a9557
80. feat: generate and display product summaries in the CLI and pass a cookie file argument to the agent.
Date: 2025-11-26
Author: ssunggun2
Hash: e055127
Changes
agent/interactive_shopping_cli.py | 14 +++++++++++++
 agent/llm_utils.py                | 44 +++++++++++++++++++++++++++++++++++++++
 run_agent.sh                      |  2 +-
 3 files changed, 59 insertions(+), 1 deletion(-)
81. feat: Remove old RAG components and crawling pipeline, and refactor agent configuration and LLM integration.
Date: 2025-11-26
Author: ssunggun2
Hash: da5cdc5
Changes
agent/config.py                                    |  141 +++
 agent/coupang_playwright_agent.py                  |   59 +-
 agent/coupang_scenario_pipeline.py                 |   17 +-
 agent/coupang_search_agent.py                      |   37 +-
 agent/infra/__init__.py                            |    0
 agent/{llm_utils.py => infra/llm.py}               |   76 +-
 agent/interactive_cli/artifacts.py                 |    2 +-
 agent/interactive_shopping_cli.py                  |   55 +-
 agent/utils.py                                     |   57 +
 crawling/btf.py                                    |  149 +--
 crawling/crawl_category_urls.py                    |  261 ----
 crawling/fetch_html.py                             |  141 +--
 crawling/inquiries.py                              |  126 +-
 crawling/main.py                                   |  505 --------
 crawling/make_products_csv.py                      |  372 ------
 crawling/quantity.py                               |  175 +--
 crawling/review.py                                 |  123 +-
 crawling/test_pipeline.py                          |  140 ---
 main.py                                            |   62 +
 ocr.py                                             |   55 -
 preprocessing/clova_ocr_batch.py                   |  118 +-
 preprocessing/data_chunking_processor.py           |  202 +--
 preprocessing/to_schema_plus_btf.py                |  510 --------
 rag/README.md                                      |  396 ------
 rag/analyze_chunks_final.py                        |  228 ----
 rag/questions.txt                                  |   11 -
 .../8826288636/ocr_store/index.faiss               |  Bin 3117 -> 0 bytes
 .../8826288636/ocr_store/index.pkl                 |  Bin 4988 -> 0 bytes
 .../8826288636/product_store/index.faiss           |  Bin 13869 -> 0 bytes
 .../8826288636/product_store/index.pkl             |  Bin 3149 -> 0 bytes
 .../8826288636/review_store/index.faiss            |  Bin 46125 -> 0 bytes
 .../8826288636/review_store/index.pkl              |  Bin 71077 -> 0 bytes
 rag/rag_with_detail.py                             | 1281 --------------------
 rag/requirements.txt                               |   14 -
 run.sh                                             |    3 -
 run_agent.sh                                       |    2 +-
 to_schema.py                                       |  365 ------
 37 files changed, 379 insertions(+), 5304 deletions(-)
82. docs: update project README with latest information
Date: 2025-11-26
Author: ssunggun2
Hash: 2eba3f9
Changes
README.md | 87 ++++++++++++++++++++++++++++++++++-----------------------------
 1 file changed, 47 insertions(+), 40 deletions(-)
83. refactor: Reorganize data extraction into new scraper and OCR processor modules, removing old crawling and agent components.
Date: 2025-11-26
Author: ssunggun2
Hash: 915dd17
Changes
.gitignore                                         |   1 +
 README.md                                          |  93 +++--
 agent/coupang_scenario_pipeline.py                 | 402 ---------------------
 agent/infra/__init__.py                            |   0
 agent/interactive_cli/__init__.py                  |   7 -
 config/selectors.py                                |  60 +++
 agent/config.py => config/settings.py              |  69 +---
 {agent/interactive_cli => core}/cookies.py         |   0
 {agent/interactive_cli => core}/state.py           |   0
 {agent => core}/utils.py                           |   0
 crawling/README.md                                 | 164 ---------
 crawling/btf.py                                    | 184 ----------
 crawling/fetch_html.py                             | 230 ------------
 crawling/inquiries.py                              | 128 -------
 crawling/quantity.py                               | 230 ------------
 crawling/review.py                                 | 157 --------
 {agent/interactive_cli => interface}/artifacts.py  |  79 ++--
 .../cli.py                                         |  30 +-
 main.py                                            |  19 +-
 preprocessing/clova_ocr_batch.py                   | 333 -----------------
 .../chunker.py                                     |   2 +-
 processors/ocr_processor.py                        | 198 ++++++++++
 requirements.txt                                   |   1 +
 scrapers/html_fetcher.py                           | 214 +++++++++++
 scrapers/inquiry_scraper.py                        | 119 ++++++
 scrapers/product_detail_scraper.py                 | 138 +++++++
 scrapers/quantity_scraper.py                       | 210 +++++++++++
 scrapers/review_scraper.py                         | 147 ++++++++
 .../browser_service.py                             | 122 +------
 .../browser.py => services/browser_setup.py        |   0
 agent/infra/llm.py => services/llm_service.py      |   4 +-
 .../search_service.py                              |   4 +-
 32 files changed, 1238 insertions(+), 2107 deletions(-)
84. refactor: Clova OCR 관련 필드 및 로직을 제거하고 OpenAI API 키 기반의 OCR 처리기로 교체했습니다.
Date: 2025-11-26
Author: ssunggun2
Hash: e1f6907
Changes
interface/artifacts.py      |  93 +++++---------------
 interface/cli.py            |   5 +-
 main.py                     |  30 ++-----
 processors/ocr_processor.py | 202 +++++++++++++++++++-------------------------
 4 files changed, 118 insertions(+), 212 deletions(-)
85. refactor: OCR 관련 매개변수 및 변수 이름을 일반화했습니다.
Date: 2025-11-27
Author: ssunggun2
Hash: 4de040b
Changes
README.md                   |  8 +-------
 interface/artifacts.py      | 14 +++++++-------
 interface/cli.py            |  4 ++--
 main.py                     |  4 ++--
 processors/ocr_processor.py |  1 -
 5 files changed, 12 insertions(+), 19 deletions(-)
86. feat: OCR 및 BTF 아티팩트 핸들러를 추가하고 CLI를 컨트롤러와 믹스인으로 리팩토링했습니다.
Date: 2025-11-27
Author: ssunggun2
Hash: 90084c1
Changes
README.md                                          |  18 +-
 config/settings.py                                 |  19 +-
 interface/artifacts/__init__.py                    |   4 +
 interface/{artifacts.py => artifacts/collector.py} | 300 +-----------
 interface/artifacts/context.py                     |  43 ++
 interface/artifacts/handlers/btf_handler.py        | 113 +++++
 interface/artifacts/handlers/chunking_handler.py   | 111 +++++
 interface/artifacts/handlers/ocr_handler.py        |  44 ++
 interface/cli.py                                   | 528 ---------------------
 interface/cli/__init__.py                          |   3 +
 interface/cli/controller.py                        | 121 +++++
 interface/cli/mixins/browser_mixin.py              | 221 +++++++++
 interface/cli/mixins/intent_mixin.py               | 174 +++++++
 interface/cli/mixins/search_mixin.py               |  61 +++
 main.py                                            |   1 +
 15 files changed, 948 insertions(+), 813 deletions(-)
87. feat: 상품 기본 정보를 LLM 답변에 활용하고 장바구니에 수량 추가 기능을 구현하며, 아티팩트 수집 진행 상황을 사용자에게 표시합니다.
Date: 2025-11-27
Author: ssunggun2
Hash: e83ec61
Changes
config/settings.py                   |  2 +
 interface/artifacts/collector.py     | 20 ++++++++
 interface/cli/mixins/intent_mixin.py | 10 ++--
 scrapers/html_fetcher.py             | 11 ++---
 scrapers/quantity_scraper.py         |  4 +-
 services/browser_service.py          | 95 +++++++++++++++++++++++++++++++++---
 services/llm_service.py              | 33 ++++++-------
 7 files changed, 137 insertions(+), 38 deletions(-)
88. feat: Playwright에서 미리 로드된 HTML을 사용한 데이터 수집을 지원하고, curl 대체 시 'Access Denied' 응답을 처리합니다.
Date: 2025-11-27
Author: ssunggun2
Hash: 74e8423
Changes
_curl_html_487322.html                |  10 ++
 interface/artifacts/collector.py      | 182 ++++++++++++++++++++++++++--------
 interface/cli/mixins/browser_mixin.py |  13 ++-
 scrapers/html_fetcher.py              |   6 +-
 4 files changed, 168 insertions(+), 43 deletions(-)
89. feat: JSON-LD 스키마 파싱을 우선하고 상세 DOM 선택자를 폴백으로 사용하여 제품 정보 추출 로직을 개선하고 더 많은 정보를 추가합니다.
Date: 2025-11-27
Author: ssunggun2
Hash: 955fc3f
Changes
services/browser_service.py | 210 +++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 189 insertions(+), 21 deletions(-)
90. feat: curl_cffi를 사용하여 스크래핑 우회 로직을 강화하고, 멀티모달 RAG를 위한 BTF 이미지 매핑을 추가하며, 브라우저 설정 및 User-Agent를 업데이트했습니다.
Date: 2025-11-27
Author: ssunggun2
Hash: 5b9d45e
Changes
README.md                                        |  53 ++++++-
 _curl_html_487322.html                           |  10 --
 interface/artifacts/collector.py                 | 173 ++++++++++++++++++-----
 interface/artifacts/context.py                   |   5 +
 interface/artifacts/handlers/btf_handler.py      |  13 +-
 interface/artifacts/handlers/chunking_handler.py |   7 +-
 interface/cli/mixins/browser_mixin.py            |   2 +-
 processors/chunker.py                            |  80 +++++++++--
 scrapers/quantity_scraper.py                     |  87 ++++++++++--
 services/browser_service.py                      |  21 +--
 services/browser_setup.py                        |   4 +
 services/llm_service.py                          | 118 ++++++++++++++--
 12 files changed, 467 insertions(+), 106 deletions(-)
91. fix: HTML에서 itemId 및 vendorItemId 추출 로직을 분리하고 정규 표현식 패턴을 개선하여 수정
Date: 2025-11-28
Author: ssunggun2
Hash: 09c4366
Changes
interface/artifacts/collector.py | 67 +++++++++++++++++++++++++++-------------
 1 file changed, 46 insertions(+), 21 deletions(-)
92. Include OCR data in chunk dataset
Date: 2025-11-28
Author: 5sudeng
Hash: 7e13f28
Changes
interface/artifacts/handlers/chunking_handler.py | 10 ++++
 processors/chunker.py                            | 75 ++++++++++++++++++++----
 2 files changed, 73 insertions(+), 12 deletions(-)
93. feat: 임시 파일 건너뛰기 로직을 추가하고 상품 가격 추출 로직을 개선했습니다.
Date: 2025-11-29
Author: ssunggun2
Hash: 0c1dff1
Changes
interface/artifacts/handlers/chunking_handler.py |  3 ++
 services/search_service.py                       | 41 ++++++++++++++++++++++--
 2 files changed, 42 insertions(+), 2 deletions(-)
94. feat: Enhance user feedback and error handling in CLI and browser mixins
Date: 2025-11-29
Author: 5sudeng
Hash: 663b200
Changes
interface/artifacts/collector.py      |  7 +++++++
 interface/cli/controller.py           |  9 +++++++++
 interface/cli/mixins/browser_mixin.py | 37 ++++++++++++++++++++++++++++++++---
 interface/cli/mixins/intent_mixin.py  | 19 ++++++++++++++++--
 interface/cli/mixins/search_mixin.py  | 11 ++++++++++-
 main.py                               |  5 ++++-
 6 files changed, 81 insertions(+), 7 deletions(-)
95. feat: 장바구니 페이지로 이동하는 기능과 해당 인텐트 처리 로직을 추가했습니다.
Date: 2025-11-29
Author: ssunggun2
Hash: 64f76b3
Changes
config/settings.py          | 17 ++++++++--------
 services/browser_service.py | 49 +++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 58 insertions(+), 8 deletions(-)
96. feat: Add navigate_to_cart intent and handler
Date: 2025-11-29
Author: ssunggun2
Hash: e1ce6e7
Changes
interface/cli/mixins/intent_mixin.py | 13 ++++++++++++-
 1 file changed, 12 insertions(+), 1 deletion(-)
97. Merge branch 'main' of https://github.com/5sudeng/DS_project
Date: 2025-11-29
Author: ssunggun2
Hash: 1a0065a
98. re-packaging
Date: 2025-12-01
Author: 
terajunha@snu.ac.kr
Hash: b635204
Changes
core/voice_io.py                      | 496 ++++++++++++++++++++++++++++++++++
 interface/cli/controller.py           |  19 +-
 interface/cli/mixins/browser_mixin.py |   6 +-
 interface/cli/mixins/io_mixin.py      |   0
 interface/cli/mixins/search_mixin.py  |   6 +-
 main.py                               |   6 +
 6 files changed, 526 insertions(+), 7 deletions(-)
99. refactor: 브라우저 뷰포트 크기 명시적 설정을 제거했습니다.
Date: 2025-12-01
Author: ssunggun2
Hash: 73a06e8
Changes
services/browser_setup.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
100. re-packaging
Date: 2025-12-01
Author: 
terajunha@snu.ac.kr
Hash: c868def
Changes
config/selectors.py                   |  41 ++++
 config/settings.py                    |  35 +++-
 core/state.py                         |   2 +-
 core/vito-stt-client.proto            | 224 +++++++++++++++++++++
 core/vito_stt_client_pb2.py           |  45 +++++
 core/vito_stt_client_pb2_grpc.py      |  70 +++++++
 core/voice_io.py                      |  87 +++++---
 interface/cli/controller.py           |  49 +++--
 interface/cli/mixins/browser_mixin.py | 197 +++++-------------
 interface/cli/mixins/intent_mixin.py  | 367 +++++++++++++++++++++++++++-------
 interface/cli/mixins/io_mixin.py      | 128 ++++++++++++
 interface/cli/mixins/search_mixin.py  |  60 ++++--
 main.py                               |  12 +-
 openai_voice_env.txt                  |   4 +
 rtzr_voice_env.txt                    |   4 +
 services/browser_service.py           |  75 ++++---
 services/llm_service.py               | 243 ++++++++++++++++++++++
 services/product_info_parser.py       |  93 +++++++++
 services/product_navigator.py         | 143 +++++++++++++
 services/result_types.py              |  54 +++++
 services/search_service.py            | 185 +++++++++++++++--
 21 files changed, 1785 insertions(+), 333 deletions(-)
101. Merge branch 'main_p' of https://github.com/5sudeng/DS_project into main_p
Date: 2025-12-01
Author: 
terajunha@snu.ac.kr
Hash: 6a55ff4
102. feat: 키보드 음성 입력(PTT) 기능을 오디오 녹음 방식으로 개선하고 STT 백엔드 선택 옵션을 추가했습니다.
Date: 2025-12-01
Author: ssunggun2
Hash: 387d095
Changes
core/voice_io.py                 | 125 +++++++++++++++++++++++++++++++--------
 interface/cli/controller.py      |   2 +
 interface/cli/mixins/io_mixin.py |   1 -
 main.py                          |   1 +
 run_agent.sh                     |   2 +-
 5 files changed, 104 insertions(+), 27 deletions(-)
103. feat: 검색 결과 요약 및 음성 출력 기능을 추가하고, 검색 결과 표시 방식을 개선하며, 출력 로직을 표준화했습니다.
Date: 2025-12-01
Author: ssunggun2
Hash: a3420c0
Changes
config/selectors.py                   |   5 ++
 config/settings.py                    |  16 +++++
 core/state.py                         |   1 +
 core/voice_io.py                      |  85 ++++++++++++++++++++++----
 interface/cli/controller.py           |   6 +-
 interface/cli/mixins/browser_mixin.py |   2 +-
 interface/cli/mixins/intent_mixin.py  |   1 +
 interface/cli/mixins/io_mixin.py      |   6 +-
 interface/cli/mixins/search_mixin.py  |  41 +++++++++++--
 services/llm_service.py               |  36 ++++++++++-
 services/result_types.py              |   1 +
 services/search_service.py            | 110 ++++++++++++++++++++++++----------
 12 files changed, 252 insertions(+), 58 deletions(-)
104. fix: 하이픈으로 시작하는 텍스트에 공백을 추가하여 TTS 처리 개선
Date: 2025-12-01
Author: ssunggun2
Hash: a1a46fa
Changes
core/voice_io.py | 8 ++++++++
 1 file changed, 8 insertions(+)
105. 페이지 이동, 상품 이동, 배송비 옵션 구현 수정
Date: 2025-12-02
Author: 
hjunseoh8@gmail.com
Hash: ed4833d
Changes
config/selectors.py                   |  12 +-
 config/settings.py                    |  40 ++++
 core/state.py                         |  14 ++
 interface/cli/mixins/browser_mixin.py |   2 +-
 interface/cli/mixins/intent_mixin.py  | 202 +++++++++++-----
 interface/cli/mixins/io_mixin.py      |  18 +-
 interface/cli/mixins/search_mixin.py  | 349 ++++++++++++++++++++++++++-
 services/search_service.py            | 437 +++++++++++++++++++++++++++++++---
 8 files changed, 956 insertions(+), 118 deletions(-)
106. .
Date: 2025-12-02
Author: 
hjunseoh8@gmail.com
Hash: 6168ab5
Changes
interface/cli/mixins/intent_mixin.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
107. 음성 안내문 개선
Date: 2025-12-02
Author: 
hjunseoh8@gmail.com
Hash: 64809a4
Changes
interface/cli/controller.py           | 14 +++++------
 interface/cli/mixins/browser_mixin.py | 23 +++++++++---------
 interface/cli/mixins/intent_mixin.py  | 44 +++++++++++++++++++++--------------
 interface/cli/mixins/search_mixin.py  | 37 +++++++++++------------------
 4 files changed, 57 insertions(+), 61 deletions(-)
108. refactor: CLI 출력 메시지를 간결하고 명확하게 개선했습니다.
Date: 2025-12-02
Author: ssunggun2
Hash: 4b8105b
Changes
config/settings.py                    |   2 +-
 core/voice_io.py                      | 120 +++++++++++++---------------------
 interface/cli/controller.py           |  12 ++--
 interface/cli/mixins/browser_mixin.py |  21 +++---
 interface/cli/mixins/intent_mixin.py  |  87 ++++++++++++++++--------
 interface/cli/mixins/search_mixin.py  |  54 +++++----------
 processors/ocr_processor.py           |   1 +
 services/search_service.py            |   2 +-
 8 files changed, 144 insertions(+), 155 deletions(-)
109. refactor: io_output을 console_print로 대체하여 출력 방식을 통일합니다.
Date: 2025-12-02
Author: ssunggun2
Hash: 16e9c2f
Changes
interface/cli/mixins/intent_mixin.py | 2 +-
 interface/cli/mixins/search_mixin.py | 6 +++---
 2 files changed, 4 insertions(+), 4 deletions(-)
110. feat: 검색 결과를 기본 웹 브라우저로 열 수 있는 기능을 추가했습니다.
Date: 2025-12-02
Author: ssunggun2
Hash: 43c0f27
Changes
interface/cli/mixins/search_mixin.py | 10 +++++-----
 1 file changed, 5 insertions(+), 5 deletions(-)
111. keyboard 없이 voice는 동기적으로 처리가능
Date: 2025-12-02
Author: 
terajunha@snu.ac.kr
Hash: 2a5d6da
Changes
core/voice_io.py                     | 16 ++++++++--------
 interface/cli/mixins/io_mixin.py     |  4 +++-
 interface/cli/mixins/search_mixin.py |  4 ++--
 3 files changed, 13 insertions(+), 11 deletions(-)
112. 요약문만 나오게 & 안내문 수정
Date: 2025-12-02
Author: 
hjunseoh8@gmail.com
Hash: e10577f
Changes
core/state.py                        |   3 +
 interface/cli/mixins/intent_mixin.py |  44 ++----
 interface/cli/mixins/search_mixin.py | 282 ++++++++++++++++-------------------
 3 files changed, 147 insertions(+), 182 deletions(-)
113. 카테고리별 메모리 저장 및 사용자 개인화
Date: 2025-12-02
Author: 
terajunha@snu.ac.kr
Hash: 1962f0a
Changes
core/state.py                         |   1 +
 identity.txt                          |   1 +
 interface/cli/mixins/browser_mixin.py |   2 +
 interface/cli/mixins/intent_mixin.py  |  50 ++++++--
 interface/cli/mixins/search_mixin.py  |  22 ++++
 memory.txt                            |  15 +++
 services/llm_service.py               | 207 ++++++++++++++++++++++++++++------
 7 files changed, 256 insertions(+), 42 deletions(-)
114. 말하기 속도 조절
Date: 2025-12-02
Author: 
terajunha@snu.ac.kr
Hash: c2f1508
Changes
core/voice_io.py |  2 +-
 memory.json      | 20 ++++++++++++++++++++
 2 files changed, 21 insertions(+), 1 deletion(-)
115. 일반 안내 True
Date: 2025-12-03
Author: 
terajunha@snu.ac.kr
Hash: 8d4fce9
Changes
core/state.py                        |  2 +-
 identity.txt                         |  1 -
 interface/cli/mixins/intent_mixin.py |  4 +++
 services/llm_service.py              | 58 +++++++++++++++++++++++++++++-------
 4 files changed, 52 insertions(+), 13 deletions(-)
116. re-query
Date: 2025-12-03
Author: 
terajunha@snu.ac.kr
Hash: d74ef88
Changes
services/llm_service.py | 14 ++++----------
 1 file changed, 4 insertions(+), 10 deletions(-)