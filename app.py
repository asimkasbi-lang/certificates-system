"""
نظام استخراج الشهادات الدراسية
Certificate Extraction System
FuticFlow Automation Systems © 2026
"""

import os, re, json, uuid, hashlib, logging, threading
from io import BytesIO
from functools import lru_cache
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, abort, make_response
from pypdf import PdfReader, PdfWriter

# ─────────────────────────────────────────
# Embedded HTML Templates
# ─────────────────────────────────────────
import base64 as _b64
import base64 as _b64
INDEX_HTML = _b64.b64decode("PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9ImFyIiBkaXI9InJ0bCI+CjxoZWFkPgogIDxtZXRhIGNoYXJzZXQ9IlVURi04Ii8+CiAgPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCwgaW5pdGlhbC1zY2FsZT0xLjAiLz4KICA8dGl0bGU+e3sgc2Nob29sLm5hbWVfYXIgfX0gLSDYqNmI2KfYqNipINin2YTYtNmH2KfYr9in2Ko8L3RpdGxlPgogIDxzdHlsZT4KICAgIDpyb290IHsKICAgICAgLS1icmFuZDoge3sgc2Nob29sLmNvbG9yIH19OwogICAgICAtLWJyYW5kLWRhcms6IGNvbG9yLW1peChpbiBzcmdiLCB7eyBzY2hvb2wuY29sb3IgfX0gODAlLCBibGFjayk7CiAgICAgIC0tcmFkaXVzOiAxNnB4OwogICAgfQoKICAgICogeyBib3gtc2l6aW5nOiBib3JkZXItYm94OyBtYXJnaW46IDA7IHBhZGRpbmc6IDA7IH0KCiAgICBib2R5IHsKICAgICAgZm9udC1mYW1pbHk6ICdTZWdvZSBVSScsIFRhaG9tYSwgQXJpYWwsIHNhbnMtc2VyaWY7CiAgICAgIGJhY2tncm91bmQ6ICNmMGY0Zjg7CiAgICAgIG1pbi1oZWlnaHQ6IDEwMHZoOwogICAgICBkaXNwbGF5OiBmbGV4OwogICAgICBmbGV4LWRpcmVjdGlvbjogY29sdW1uOwogICAgICBhbGlnbi1pdGVtczogY2VudGVyOwogICAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjsKICAgICAgcGFkZGluZzogMjBweDsKICAgIH0KCiAgICAvKiDilIDilIAgQ2FyZCDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAgKi8KICAgIC5jYXJkIHsKICAgICAgYmFja2dyb3VuZDogI2ZmZjsKICAgICAgYm9yZGVyLXJhZGl1czogdmFyKC0tcmFkaXVzKTsKICAgICAgYm94LXNoYWRvdzogMCA0cHggMjRweCByZ2JhKDAsMCwwLC4xMCk7CiAgICAgIHBhZGRpbmc6IDQwcHggMzZweDsKICAgICAgd2lkdGg6IDEwMCU7CiAgICAgIG1heC13aWR0aDogNDgwcHg7CiAgICAgIHRleHQtYWxpZ246IGNlbnRlcjsKICAgIH0KCiAgICAvKiDilIDilIAgSGVhZGVyIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgCAqLwogICAgLnNjaG9vbC1uYW1lIHsKICAgICAgZm9udC1zaXplOiAxLjVyZW07CiAgICAgIGZvbnQtd2VpZ2h0OiA4MDA7CiAgICAgIGNvbG9yOiAjMWUyOTNiOwogICAgICBsaW5lLWhlaWdodDogMS40OwogICAgICBtYXJnaW4tYm90dG9tOiA2cHg7CiAgICB9CiAgICAucG9ydGFsLXRpdGxlIHsKICAgICAgZm9udC1zaXplOiAxcmVtOwogICAgICBjb2xvcjogIzY0NzQ4YjsKICAgICAgbWFyZ2luLWJvdHRvbTogMzJweDsKICAgIH0KCiAgICAvKiDilIDilIAgSW5wdXQgZ3JvdXAg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSAICovCiAgICAubGFiZWwgewogICAgICBkaXNwbGF5OiBibG9jazsKICAgICAgZm9udC1zaXplOiAuOTVyZW07CiAgICAgIGZvbnQtd2VpZ2h0OiA3MDA7CiAgICAgIGNvbG9yOiAjMzM0MTU1OwogICAgICBtYXJnaW4tYm90dG9tOiAxMHB4OwogICAgICB0ZXh0LWFsaWduOiByaWdodDsKICAgIH0KICAgIGlucHV0W3R5cGU9InRleHQiXSB7CiAgICAgIHdpZHRoOiAxMDAlOwogICAgICBwYWRkaW5nOiAxNHB4IDE2cHg7CiAgICAgIGJvcmRlcjogMnB4IHNvbGlkICNlMmU4ZjA7CiAgICAgIGJvcmRlci1yYWRpdXM6IDEwcHg7CiAgICAgIGZvbnQtc2l6ZTogMXJlbTsKICAgICAgdGV4dC1hbGlnbjogY2VudGVyOwogICAgICBsZXR0ZXItc3BhY2luZzogMnB4OwogICAgICBkaXJlY3Rpb246IGx0cjsKICAgICAgdHJhbnNpdGlvbjogYm9yZGVyLWNvbG9yIC4yczsKICAgICAgb3V0bGluZTogbm9uZTsKICAgIH0KICAgIGlucHV0W3R5cGU9InRleHQiXTpmb2N1cyB7IGJvcmRlci1jb2xvcjogdmFyKC0tYnJhbmQpOyB9CgogICAgLyog4pSA4pSAIEJ1dHRvbiDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAgKi8KICAgIC5idG4gewogICAgICBkaXNwbGF5OiBmbGV4OwogICAgICBhbGlnbi1pdGVtczogY2VudGVyOwogICAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjsKICAgICAgZ2FwOiA4cHg7CiAgICAgIHdpZHRoOiAxMDAlOwogICAgICBtYXJnaW4tdG9wOiAxOHB4OwogICAgICBwYWRkaW5nOiAxNXB4OwogICAgICBiYWNrZ3JvdW5kOiB2YXIoLS1icmFuZCk7CiAgICAgIGNvbG9yOiAjZmZmOwogICAgICBib3JkZXI6IG5vbmU7CiAgICAgIGJvcmRlci1yYWRpdXM6IDEwcHg7CiAgICAgIGZvbnQtc2l6ZTogMS4wNXJlbTsKICAgICAgZm9udC13ZWlnaHQ6IDcwMDsKICAgICAgY3Vyc29yOiBwb2ludGVyOwogICAgICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kIC4ycywgdHJhbnNmb3JtIC4xczsKICAgIH0KICAgIC5idG46aG92ZXIgIHsgYmFja2dyb3VuZDogdmFyKC0tYnJhbmQtZGFyayk7IH0KICAgIC5idG46YWN0aXZlIHsgdHJhbnNmb3JtOiBzY2FsZSguOTgpOyB9CiAgICAuYnRuOmRpc2FibGVkIHsgb3BhY2l0eTogLjY7IGN1cnNvcjogbm90LWFsbG93ZWQ7IH0KCiAgICAvKiDilIDilIAgU3Bpbm5lciDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAgKi8KICAgIC5zcGlubmVyIHsKICAgICAgd2lkdGg6IDE4cHg7IGhlaWdodDogMThweDsKICAgICAgYm9yZGVyOiAzcHggc29saWQgcmdiYSgyNTUsMjU1LDI1NSwuNCk7CiAgICAgIGJvcmRlci10b3AtY29sb3I6ICNmZmY7CiAgICAgIGJvcmRlci1yYWRpdXM6IDUwJTsKICAgICAgYW5pbWF0aW9uOiBzcGluIC43cyBsaW5lYXIgaW5maW5pdGU7CiAgICB9CiAgICBAa2V5ZnJhbWVzIHNwaW4geyB0byB7IHRyYW5zZm9ybTogcm90YXRlKDM2MGRlZyk7IH0gfQoKICAgIC8qIOKUgOKUgCBSZXN1bHQgcGFuZWwg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSAICovCiAgICAucmVzdWx0IHsKICAgICAgbWFyZ2luLXRvcDogMjRweDsKICAgICAgcGFkZGluZzogMThweCAyMHB4OwogICAgICBib3JkZXItcmFkaXVzOiAxMnB4OwogICAgICBmb250LXNpemU6IC45NXJlbTsKICAgICAgbGluZS1oZWlnaHQ6IDEuNzsKICAgICAgZGlzcGxheTogbm9uZTsKICAgIH0KICAgIC5yZXN1bHQuc3VjY2VzcyB7CiAgICAgIGJhY2tncm91bmQ6ICNmMGZkZjQ7CiAgICAgIGJvcmRlcjogMS41cHggc29saWQgIzg2ZWZhYzsKICAgICAgY29sb3I6ICMxNjY1MzQ7CiAgICAgIGRpc3BsYXk6IGJsb2NrOwogICAgfQogICAgLnJlc3VsdC5lcnJvciB7CiAgICAgIGJhY2tncm91bmQ6ICNmZWYyZjI7CiAgICAgIGJvcmRlcjogMS41cHggc29saWQgI2ZjYTVhNTsKICAgICAgY29sb3I6ICM5OTFiMWI7CiAgICAgIGRpc3BsYXk6IGJsb2NrOwogICAgfQogICAgLnJlc3VsdC10aXRsZSB7CiAgICAgIGZvbnQtd2VpZ2h0OiA4MDA7CiAgICAgIGZvbnQtc2l6ZTogMS4wNXJlbTsKICAgICAgbWFyZ2luLWJvdHRvbTogMTBweDsKICAgIH0KCiAgICAvKiDilIDilIAgRG93bmxvYWQgYnV0dG9uIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgCAqLwogICAgLmRsLWJ0biB7CiAgICAgIGRpc3BsYXk6IGlubGluZS1mbGV4OwogICAgICBhbGlnbi1pdGVtczogY2VudGVyOwogICAgICBnYXA6IDhweDsKICAgICAgbWFyZ2luLXRvcDogMTRweDsKICAgICAgcGFkZGluZzogMTNweCAyOHB4OwogICAgICBiYWNrZ3JvdW5kOiB2YXIoLS1icmFuZCk7CiAgICAgIGNvbG9yOiAjZmZmOwogICAgICB0ZXh0LWRlY29yYXRpb246IG5vbmU7CiAgICAgIGJvcmRlci1yYWRpdXM6IDEwcHg7CiAgICAgIGZvbnQtc2l6ZTogMXJlbTsKICAgICAgZm9udC13ZWlnaHQ6IDcwMDsKICAgICAgdHJhbnNpdGlvbjogYmFja2dyb3VuZCAuMnM7CiAgICB9CiAgICAuZGwtYnRuOmhvdmVyIHsgYmFja2dyb3VuZDogdmFyKC0tYnJhbmQtZGFyayk7IH0KCiAgICAvKiDilIDilIAgRm9vdGVyIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgCAqLwogICAgZm9vdGVyIHsKICAgICAgbWFyZ2luLXRvcDogMjhweDsKICAgICAgZm9udC1zaXplOiAuNzhyZW07CiAgICAgIGNvbG9yOiAjOTRhM2I4OwogICAgICB0ZXh0LWFsaWduOiBjZW50ZXI7CiAgICAgIGxpbmUtaGVpZ2h0OiAxLjc7CiAgICB9CiAgPC9zdHlsZT4KPC9oZWFkPgo8Ym9keT4KCjxkaXYgY2xhc3M9ImNhcmQiPgogIDxwIHN0eWxlPSJmb250LXNpemU6Mi40cmVtOyBtYXJnaW4tYm90dG9tOjhweDsiPnt7IHNjaG9vbC5lbW9qaSB9fTwvcD4KICA8aDEgY2xhc3M9InNjaG9vbC1uYW1lIj57eyBzY2hvb2wubmFtZV9hciB9fTwvaDE+CiAgPHAgY2xhc3M9InBvcnRhbC10aXRsZSI+2KjZiNin2KjYqSDYp9iz2KrYrtix2KfYrCDYp9mE2LTZh9in2K/Yp9iqINin2YTYr9ix2KfYs9mK2Kk8L3A+CgogIDxsYWJlbCBjbGFzcz0ibGFiZWwiIGZvcj0iY2l2aWxfaWQiPtin2YTYsdmC2YUg2KfZhNmF2K/ZhtmKINmE2YTYt9in2YTYqDo8L2xhYmVsPgogIDxpbnB1dCB0eXBlPSJ0ZXh0IiBpZD0iY2l2aWxfaWQiIG1heGxlbmd0aD0iOCIgaW5wdXRtb2RlPSJudW1lcmljIgogICAgICAgICBwbGFjZWhvbGRlcj0i2KPYr9iu2YQg2KfZhNix2YLZhSDYp9mE2YXYr9mG2Yog2KfZhNmF2YPZiNmGINmF2YYgNyDYo9mIIDgg2KPYsdmC2KfZhSIKICAgICAgICAgb25pbnB1dD0idGhpcy52YWx1ZT10aGlzLnZhbHVlLnJlcGxhY2UoL1xEL2csJycpIi8+CgogIDxidXR0b24gY2xhc3M9ImJ0biIgaWQ9InNlYXJjaEJ0biIgb25jbGljaz0ic2VhcmNoKCkiPgogICAgPHNwYW4gaWQ9ImJ0blRleHQiPvCflI0g2KfYqNit2Ksg2LnZhiDYp9mE2LTZh9in2K/YqTwvc3Bhbj4KICAgIDxzcGFuIGlkPSJidG5TcGlubmVyIiBjbGFzcz0ic3Bpbm5lciIgc3R5bGU9ImRpc3BsYXk6bm9uZSI+PC9zcGFuPgogIDwvYnV0dG9uPgoKICA8ZGl2IGlkPSJyZXN1bHQiPjwvZGl2Pgo8L2Rpdj4KCjxmb290ZXI+CiAg2KrZhSDYp9mE2KrYt9mI2YrYsSDZiNin2YTYqti32KjZitmCINio2YjYp9iz2LfYqSDYo9iu2LXYp9im2Yog2YbYuNmFINmF2K/Ysdiz2YrYqTog2LnYp9i12YUg2YbYp9i12LEg2KfZhNmD2KfYs9io2Yo8YnIvPgogIEZ1dGljRmxvdyBBdXRvbWF0aW9uIFN5c3RlbXMgwqkgMjAyNgo8L2Zvb3Rlcj4KCjxzY3JpcHQ+CiAgY29uc3QgaW5wdXQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnY2l2aWxfaWQnKTsKICBpbnB1dC5hZGRFdmVudExpc3RlbmVyKCdrZXlkb3duJywgZSA9PiB7IGlmIChlLmtleSA9PT0gJ0VudGVyJykgc2VhcmNoKCk7IH0pOwoKICBhc3luYyBmdW5jdGlvbiBzZWFyY2goKSB7CiAgICBjb25zdCBjaXZpbF9pZCA9IGlucHV0LnZhbHVlLnRyaW0oKTsKICAgIGNvbnN0IGJ0biAgICAgID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3NlYXJjaEJ0bicpOwogICAgY29uc3QgYnRuVGV4dCAgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnYnRuVGV4dCcpOwogICAgY29uc3Qgc3Bpbm5lciAgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnYnRuU3Bpbm5lcicpOwogICAgY29uc3QgcmVzdWx0RWwgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgncmVzdWx0Jyk7CgogICAgaWYgKCEvXlxkezcsOH0kLy50ZXN0KGNpdmlsX2lkKSkgewogICAgICBzaG93RXJyb3IoJ9mK2LHYrNmJINil2K/Yrtin2YQg2LHZgtmFINmF2K/ZhtmKINi12K3ZititINmF2YPZiNmGINmF2YYgNyDYo9mIIDgg2KPYsdmC2KfZhS4nKTsKICAgICAgcmV0dXJuOwogICAgfQoKICAgIC8vIExvYWRpbmcgc3RhdGUKICAgIGJ0bi5kaXNhYmxlZCAgID0gdHJ1ZTsKICAgIGJ0blRleHQuc3R5bGUuZGlzcGxheSAgPSAnbm9uZSc7CiAgICBzcGlubmVyLnN0eWxlLmRpc3BsYXkgID0gJ2lubGluZS1ibG9jayc7CiAgICByZXN1bHRFbC5jbGFzc05hbWUgICAgID0gJyc7CiAgICByZXN1bHRFbC5zdHlsZS5kaXNwbGF5ID0gJ25vbmUnOwogICAgcmVzdWx0RWwuaW5uZXJIVE1MICAgICA9ICcnOwoKICAgIHRyeSB7CiAgICAgIGNvbnN0IHJlcyAgPSBhd2FpdCBmZXRjaCgnL2FwaS9zZWFyY2gnLCB7CiAgICAgICAgbWV0aG9kOiAgJ1BPU1QnLAogICAgICAgIGhlYWRlcnM6IHsgJ0NvbnRlbnQtVHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJyB9LAogICAgICAgIGJvZHk6ICAgIEpTT04uc3RyaW5naWZ5KHsgY2l2aWxfaWQgfSkKICAgICAgfSk7CiAgICAgIGNvbnN0IGRhdGEgPSBhd2FpdCByZXMuanNvbigpOwoKICAgICAgaWYgKGRhdGEuc3VjY2VzcykgewogICAgICAgIHNob3dTdWNjZXNzKGRhdGEpOwogICAgICB9IGVsc2UgewogICAgICAgIHNob3dFcnJvcihkYXRhLm1lc3NhZ2UgfHwgJ9it2K/YqyDYrti32KMg2LrZitixINmF2KrZiNmC2LkuJyk7CiAgICAgIH0KICAgIH0gY2F0Y2ggKGVycikgewogICAgICBzaG93RXJyb3IoJ9iq2LnYsNmR2LEg2KfZhNin2KrYtdin2YQg2KjYp9mE2K7Yp9iv2YUuINmK2LHYrNmJINin2YTZhdit2KfZiNmE2Kkg2YTYp9it2YLYp9mLLicpOwogICAgfSBmaW5hbGx5IHsKICAgICAgYnRuLmRpc2FibGVkICAgICAgICAgID0gZmFsc2U7CiAgICAgIGJ0blRleHQuc3R5bGUuZGlzcGxheSA9ICdpbmxpbmUnOwogICAgICBzcGlubmVyLnN0eWxlLmRpc3BsYXkgPSAnbm9uZSc7CiAgICB9CiAgfQoKICBmdW5jdGlvbiBzaG93U3VjY2VzcyhkYXRhKSB7CiAgICBjb25zdCBlbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdyZXN1bHQnKTsKICAgIGVsLmlubmVySFRNTCA9IGAKICAgICAgPGRpdiBjbGFzcz0icmVzdWx0LXRpdGxlIj7inIUg2KrZhSDYp9mE2LnYq9mI2LEg2LnZhNmJINin2YTYtNmH2KfYr9ipITwvZGl2PgogICAgICA8cD7ZitmF2YPZhtmDINiq2K3ZhdmK2YQg2KfZhNi02YfYp9iv2Kkg2KfZhNiv2LHYp9iz2YrYqSDYudio2LEg2KfZhNix2KfYqNi3INij2K/Zhtin2YcuPC9wPgogICAgICA8cCBzdHlsZT0iZm9udC1zaXplOi44MnJlbTtjb2xvcjojMTY2NTM0O21hcmdpbi10b3A6NnB4OyI+CiAgICAgICAg4o+xINin2YTYsdin2KjYtyDYtdin2YTYrSDZhNmF2K/YqSAke2RhdGEuZXhwaXJlc19ob3Vyc30g2LPYp9i52Kkg4oCUINmK2YXZg9mG2YMg2KfZhNix2KzZiNi5INil2YTZitmHINmB2Yog2KPZiiDZiNmC2KouCiAgICAgIDwvcD4KICAgICAgPGEgY2xhc3M9ImRsLWJ0biIgaHJlZj0iJHtkYXRhLmRvd25sb2FkX3VybH0iIHRhcmdldD0iX2JsYW5rIiByZWw9Im5vb3BlbmVyIj4KICAgICAgICDwn5OEINiq2K3ZhdmK2YQg2KfZhNi02YfYp9iv2Kkg2KfZhNiv2LHYp9iz2YrYqQogICAgICA8L2E+CiAgICBgOwogICAgZWwuc3R5bGUuY3NzVGV4dCA9ICdkaXNwbGF5OmJsb2NrOyBiYWNrZ3JvdW5kOiNmMGZkZjQ7IGJvcmRlcjoxLjVweCBzb2xpZCAjODZlZmFjOyBjb2xvcjojMTY2NTM0OyBtYXJnaW4tdG9wOjI0cHg7IHBhZGRpbmc6MThweCAyMHB4OyBib3JkZXItcmFkaXVzOjEycHg7IGZvbnQtc2l6ZTouOTVyZW07IGxpbmUtaGVpZ2h0OjEuNzsnOwogIH0KCiAgZnVuY3Rpb24gc2hvd0Vycm9yKG1zZykgewogICAgY29uc3QgZWwgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgncmVzdWx0Jyk7CiAgICBlbC5pbm5lckhUTUwgPSBgPGRpdiBjbGFzcz0icmVzdWx0LXRpdGxlIj7inYwg2YTZhSDZitiq2YUg2KfZhNi52KvZiNixINi52YTZiSDYp9mE2LTZh9in2K/YqTwvZGl2PjxwPiR7bXNnfTwvcD5gOwogICAgZWwuc3R5bGUuY3NzVGV4dCA9ICdkaXNwbGF5OmJsb2NrOyBiYWNrZ3JvdW5kOiNmZWYyZjI7IGJvcmRlcjoxLjVweCBzb2xpZCAjZmNhNWE1OyBjb2xvcjojOTkxYjFiOyBtYXJnaW4tdG9wOjI0cHg7IHBhZGRpbmc6MThweCAyMHB4OyBib3JkZXItcmFkaXVzOjEycHg7IGZvbnQtc2l6ZTouOTVyZW07IGxpbmUtaGVpZ2h0OjEuNzsnOwogIH0KPC9zY3JpcHQ+CjwvYm9keT4KPC9odG1sPgo=").decode("utf-8")
ERROR_HTML = _b64.b64decode("PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9ImFyIiBkaXI9InJ0bCI+CjxoZWFkPgogIDxtZXRhIGNoYXJzZXQ9IlVURi04Ii8+CiAgPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCwgaW5pdGlhbC1zY2FsZT0xLjAiLz4KICA8dGl0bGU+2K7Yt9ijIC0g2KjZiNin2KjYqSDYp9mE2LTZh9in2K/Yp9iqPC90aXRsZT4KICA8c3R5bGU+CiAgICBib2R5IHsgZm9udC1mYW1pbHk6IEFyaWFsLCBzYW5zLXNlcmlmOyBkaXNwbGF5OiBmbGV4OyBhbGlnbi1pdGVtczogY2VudGVyOwogICAgICAgICAgIGp1c3RpZnktY29udGVudDogY2VudGVyOyBtaW4taGVpZ2h0OiAxMDB2aDsgYmFja2dyb3VuZDogI2YwZjRmODsgfQogICAgLmJveCB7IGJhY2tncm91bmQ6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDE2cHg7IHBhZGRpbmc6IDQwcHg7IG1heC13aWR0aDogNDQwcHg7CiAgICAgICAgICAgdGV4dC1hbGlnbjogY2VudGVyOyBib3gtc2hhZG93OiAwIDRweCAyNHB4IHJnYmEoMCwwLDAsLjEpOyB9CiAgICBoMiB7IGNvbG9yOiAjOTkxYjFiOyBtYXJnaW4tYm90dG9tOiAxNHB4OyB9CiAgICBwICB7IGNvbG9yOiAjNjQ3NDhiOyBsaW5lLWhlaWdodDogMS43OyB9CiAgICBhICB7IGRpc3BsYXk6IGlubGluZS1ibG9jazsgbWFyZ2luLXRvcDogMjBweDsgcGFkZGluZzogMTJweCAyOHB4OwogICAgICAgICBiYWNrZ3JvdW5kOiAjMTZhMzRhOyBjb2xvcjogI2ZmZjsgdGV4dC1kZWNvcmF0aW9uOiBub25lOwogICAgICAgICBib3JkZXItcmFkaXVzOiAxMHB4OyBmb250LXdlaWdodDogNzAwOyB9CiAgPC9zdHlsZT4KPC9oZWFkPgo8Ym9keT4KICA8ZGl2IGNsYXNzPSJib3giPgogICAgPHAgc3R5bGU9ImZvbnQtc2l6ZTozcmVtIj7imqDvuI88L3A+CiAgICA8aDI+2LHYp9io2Lcg2LrZitixINi12KfZhNitPC9oMj4KICAgIDxwPnt7IG1lc3NhZ2UgfX08L3A+CiAgICA8YSBocmVmPSIvIj7Yp9mE2LnZiNiv2Kkg2YTZhNio2YjYp9io2Kk8L2E+CiAgPC9kaXY+CjwvYm9keT4KPC9odG1sPgo=").decode("utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

_civil_index = {}
_index_lock  = threading.Lock()
_tokens      = {}
_tokens_lock = threading.Lock()

def load_index():
    global _civil_index
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            _civil_index = json.load(f)
        log.info("Index loaded: %d students", len(_civil_index))
        return
    log.info("Building index from PDFs...")
    try:
        import pdfplumber
    except ImportError:
        os.system("pip install pdfplumber --break-system-packages -q")
        import pdfplumber
    idx = {}
    for fname in sorted(os.listdir(PDF_DIR)):
        if not fname.endswith(".pdf"):
            continue
        path = os.path.join(PDF_DIR, fname)
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                m = re.search(r"CIVIL NO\s*:\s*(\d{7,8})", text)
                if m:
                    idx[m.group(1)] = {"file": fname, "page": i + 1}
    _civil_index = idx
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    log.info("Index built: %d students", len(idx))

def _load_tokens():
    global _tokens
    if os.path.exists(TOKEN_STORE_FILE):
        try:
            with open(TOKEN_STORE_FILE, "r") as f:
                _tokens = json.load(f)
        except:
            _tokens = {}

def _save_tokens():
    with open(TOKEN_STORE_FILE, "w") as f:
        json.dump(_tokens, f)

def _purge_expired():
    now = datetime.utcnow()
    expired = [t for t, v in _tokens.items() if datetime.fromisoformat(v["expires"]) < now]
    for t in expired:
        del _tokens[t]
    if expired:
        _save_tokens()

def create_token(civil_id):
    with _tokens_lock:
        _purge_expired()
        for tok, val in _tokens.items():
            if val["civil_id"] == civil_id:
                if datetime.fromisoformat(val["expires"]) > datetime.utcnow() + timedelta(hours=1):
                    return tok
        token = hashlib.sha256(f"{civil_id}:{uuid.uuid4()}".encode()).hexdigest()
        expires = (datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)).isoformat()
        _tokens[token] = {"civil_id": civil_id, "expires": expires}
        _save_tokens()
        return token

def resolve_token(token):
    with _tokens_lock:
        _purge_expired()
        entry = _tokens.get(token)
        if not entry:
            return None
        if datetime.fromisoformat(entry["expires"]) < datetime.utcnow():
            del _tokens[token]
            _save_tokens()
            return None
        return entry["civil_id"]

@lru_cache(maxsize=4)
def _get_reader(fname):
    return PdfReader(os.path.join(PDF_DIR, fname))

def extract_page_pdf(fname, page_num):
    reader = _get_reader(fname)
    writer = PdfWriter()
    writer.add_page(reader.pages[page_num - 1])
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()

@app.route("/")
def index_redirect():
    s = SCHOOLS["alqaqaa"]
    return INDEX_HTML.format(**s)

@app.route("/school/<school_key>")
def school_portal(school_key):
    school = SCHOOLS.get(school_key)
    if not school:
        abort(404)
    return INDEX_HTML.format(**school)

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True, silent=True) or {}
    civil_id = str(data.get("civil_id", "")).strip()
    if not re.fullmatch(r"\d{7,8}", civil_id):
        return jsonify({"success": False, "message": "الرقم المدني غير صحيح. يجب أن يكون 7 أو 8 أرقام."}), 400
    with _index_lock:
        entry = _civil_index.get(civil_id)
    if not entry:
        return jsonify({"success": False, "message": "لم يتم العثور على شهادة بهذا الرقم المدني."}), 404
    token = create_token(civil_id)
    return jsonify({"success": True, "message": "تم العثور على الشهادة!", "token": token, "download_url": f"/download/{token}", "expires_hours": TOKEN_EXPIRY_HOURS})

@app.route("/download/<token>")
def download_certificate(token):
    civil_id = resolve_token(token)
    if not civil_id:
        return ERROR_HTML.format(message="الرابط منتهي الصلاحية أو غير صحيح. الرجاء البحث مجدداً."), 410
    with _index_lock:
        entry = _civil_index.get(civil_id)
    if not entry:
        abort(404)
    try:
        pdf_bytes = extract_page_pdf(entry["file"], entry["page"])
    except Exception as e:
        log.error("PDF extraction failed: %s", e)
        abort(500)
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'inline; filename="certificate_{civil_id}.pdf"'
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.route("/health")
def health():
    return jsonify({"status": "ok", "students": len(_civil_index)})

# Load at module level so gunicorn picks it up
_load_tokens()
load_index()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
