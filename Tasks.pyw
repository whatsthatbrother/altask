# -*- coding: utf-8 -*-
"""
Tasks v4.2 — a task panel docked to the right edge of the screen (Windows 10 / 11).

- Pure Python 3 standard library (tkinter). No extra packages.
- Run: double-click Tasks.pyw  (or:  pythonw Tasks.pyw)
- Made by Diar F.
- Data: %APPDATA%\\DetyratNote\\tasks.json  (same file as v1, nothing is lost)

Shortcuts:
  Enter          add task             Ctrl+N   focus the input
  Double-click   edit task            Ctrl+Z   undo delete / clear
"""
import ctypes
import hashlib
import json
import os
import queue
import re
import sys
import tempfile
import threading
import urllib.request
import uuid
from datetime import datetime
import tkinter as tk
from tkinter import font as tkfont

VERSION = "4.2"
AUTHOR = "Diar F."
try:                                    # written by build.bat from repo.txt
    from update_config import UPDATE_REPO
except Exception:
    UPDATE_REPO = ""
UPDATE_MANIFEST = (f"https://github.com/{UPDATE_REPO}/releases/latest/download/latest.json"
                   if UPDATE_REPO else "")
APP_TITLE = "Tasks"
APP_ID = "Detyrat"                      # internal id (registry / mutex) kept from v1
IS_WIN = sys.platform == "win32"
DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "DetyratNote")
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")
PLACEHOLDER = "Add a new task…"

THEMES = {
    "dark": dict(
        bg_border="#2e2e34", panel="#141416", row="#1d1d21", row_hover="#26262b",
        line="#2e2e34", text="#f5f5f7", muted="#b3b3bd", faint="#7d7d88",
        accent="#ec2f33", accent2="#b8141c", accent_hover="#d6262a", done="#2fbf7a",
        danger="#ec2f33", danger_hover="#cf2226", input="#1d1d21", btn_hover="#2b2b31",
        track="#26262b", on_accent="#ffffff", scrim="#0c0c0e",
    ),
    "light": dict(
        bg_border="#dcdce1", panel="#f6f6f7", row="#ffffff", row_hover="#f4f4f6",
        line="#e4e4e8", text="#121216", muted="#4f4f5a", faint="#86868f",
        accent="#d91e24", accent2="#9f121a", accent_hover="#bf1a20", done="#1a9e62",
        danger="#d91e24", danger_hover="#b8181d", input="#ffffff", btn_hover="#ececf0",
        track="#e8e8ec", on_accent="#ffffff", scrim="#dedee3",
    ),
}

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


# app logo (PNG, base64) — generated from the same artwork as tasks.ico
LOGO_24 = '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'
LOGO_32 = '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'
LOGO_48 = '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'
LOGO_64 = 'iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAaOklEQVR42s2beZhcVZn/P+fce2tfuqq3dCfp7BsRRiIBERUVDCKg4oALoj9EH0cRBRx5ZEQWR3EQZIYRBBGU+aEjGUDEQUEYEAZwxGELIYHse3rv6q696i7n/P6oW9XVayID8/wqT+epuveeuvV9z7t+3/cKZnjps882xL33egCZk0/vCRreB0GcqdA9SrNCocWUNdN9zzSfZrxO/4Vr9fhnAdpAbJWSfVrxa4H3UPqxx/ZNxjL5NR0IUf/CkVNOWR0SxsUaPhoQMq3RuFpTVQpxWIBrR2a9Tv9la7VmxldASkxRg+QondFwv+PqG7ueeGRzM64ZBaBBClAA+VNOvVoKcXnEMMy86+IopWorhBD+ujcbbPMOH85LaTRorQFLSBk3TYqe53pKX9P5+CNXT8Y4QQD1E5vWrUsvksYvI4Z5ypjjoMAFDAFi+h/zv7fDh7qHnio7T4CZsizynvPIYD53zluefTbTLATRrPYHTzopnTACD8cta+2IbTtCYE41k/8/Ac9khlprrcFtsywr67jPucI7de5jj2eoqbGWAJx9tgSISGt9PGCtHbarjhBYoIVm8r/xm2gfgPY/aN10vPH/xLX16xvrDgF4ujV66m5PvK/WaP8PEAKsIdt24gFrrdZyPWIcs/HEiSeaix56yLvg/adc3RYInD9s244UWPoQXvpQu6t0/bP4i3ZYa1BoQByGo9WzakPzMSGEUXRdJx0ILOvt6SH1u98+8cSJJ5oCEIMnnbosZLHZUUqq2i8W032L8oEZvqfVk0OTBk9rBBAxDKQQVDyFrWtRQwoxQRx1oXpotAYJhAwDQwiqSjWijRQCja6JxBesoHYvDU2/ZzaTqemGBG1Jqdyqt3reM49vl4AWUl0WMQzT0yg0gmlUWqEJSEGLZaKajEFrsBBIBIYQdASDxEyTTfk8fxodpaw82gIBUlaAsDRQk9RZCkHStGgNBIiYJtuLRZ7JZMi6Dp3BIEnTRGlNUMiaWvuYXK0JGQZJy5pkAs1m2WSfNaEJBSpiGKZrchmgxd6TT+4OI7eYUsZc32Ymq7X2b/ZKPs+/D/Rz2eJl2LoWSSwh6KtWiRsGBc/j9v172VUs8URmhJCUJE2Lk9raeGsiyfJIlLckEg3zMIRgzHH489go+yplnhwZ5pVcnoryaA8EOTHdylGJBOfNnc/mQp754TAScLSmxbJ4fHiYl3NZLlywiIryZjU2Pe50tSkEntaFks1KGRHijIhpxm2l9FSnVxOgqyEiDf6tt5frd+7k9v176QgEcZTCEIKDlTKffvklHhoapNUK8vRohqPjCW4/8q8ouC4/2beXv9vyGggISIHnez9XKdoCFo8ND3HF1i08PjzMJ7q6+YcVq9hZKjLkVFFac9Frm7h13x7ChkHZU0QNg6FqlUte3cR3dmxjoFrBEmIWxzjB6QpHKR02ZDwYUGeYCnFWY5+1mNaZCMBWmrXJFgCu2LaFoJT8Tc8CqkqxNtnC9StX8+jwIFnX5ehEkidGhnn2xTFAY0mJQnN370GWRqIEpcRRiqhp8ofhYV7KZbGEBAE/3r8XWykCUrIoHGF3qcR70628O92KqxSdwQB7SiX+ZtNG9lfKHJtsIWUFcLSevNMzuU0Qun76LONvFy++UiDSrtICIabVIikEFaV4SzzOsG3zfDbLI0NDbCkUmB+K0BkMkXNdFkai9ITDNTDAoF2lrBRaQ1Up+qtVVkZjLIpEUMCY63Lz3t08OTKCEDW79rRmaSTKB9s7OCGV5j2tbcRMk5RlUfQ81vce5IubX2FLsUBHIMDNq49kbiiErVST9eoZo5WvDUKAcJVWYuDkdVofRuKh0ISkQYtl8eO9e7lh9w52lUoALAhHGLaruFpzTvc8Pj+/h7clkxysVPjhnt38cM9u6qJdGonym2OOZX4oxI27d3Hl9i1IBK7WrI7FuWb5St7X1kbBdflVfx93HNjHy7kciyIRDlYqPlD46zldXL10BUsiEfqrVaTgLyy0alFF9J28TotDZFpKa2KmyR9GhnlwYIDrVx2BJQUPDw7yVGaE1wp5ns5kcJtEeWp7B19fvIQT023cuGcXl762GSkElpBct3IVZ3Z2ceaLz/FCdgwN/FUiwf1rjiFqmNy2by+37d9Lb6XSMMH5oTAnpNIcEYuxrq2dY1tauGP/Pp4dG+PKZctRWh9mZTnxneg7aZ2erZyth5yUZfHzg/u5YNMrLItGuXjhYo5PpWm1LA5WK3zo+f9mxLYxfGfkac27063cu+YYgkLyyQ0v8PDQIABhw2BROMyrhQJSCCRw/9vWsq6tnd/09/PxDS+AHyWkEDhKccGChXxz8VIyjsPBSoW7+w5y18EDzAuF+a+3n4DblB/MBniyUMzDqeElkHUcPtrZxTOZDL/sPciXN78yo7BMUcsJjkkmMQBHKd6VSvPw0CCmEJQ9j1cLBQxqEaErFGJVNMZApcqKaIwWyyLrOCjfJwDcsncPt+zdM+FenYEgNx3xFkwpqLoKKaamyIfiK0ykRCs1Jc+d7uKyUly/ajVf6FnAHzOjDNpV2gIBlkWifGPra+wtl/ysraYBW4sFglISkJLXioVxtaulpig/axxzHPoqFd6VTrMhn6Xouo1rpX/dVxcs5uhEgg35LAaCFbEY70qlsaSk5HlTwM+m0Y0zQiD2v/0ELaNREMIXxNQv8LSmNRDg5j27uX3/Xm5dfRQnpNJIAXvKZb6/czt3HTww7U0/3DmHqGFwT1/vBB/RHGI1sDIa4+S2dh4Y6ONApdI4Xlfp+eEw1yxbybq2dkKGJOM4fG/ndh4fGebhY47DlHKCH5gRdE2qgECVy4g9S5ZrEQ4jkklEOFS7pS+IZicYkQYbclnWPfdsQ/2EgP5qlUXhCGXl0V+tzljA/E9fR8UTbMznCAjJnGCQg9UKntZ8uHMOt6w+koLrIoWYfv/rGi1EbaOrNl4uh1coIHYvW6nrgEU4gkgkfEFQE4S/DZ6ffv732Bi37d/L/nKZxZEIn+yey6ponLNeep5N+VxDteuveqHiHaL2rTtDT0+sKqVfhF238gjOaO/kX/sO8HQmg60U721t4wvze/DQjSJsWp6hCbiby6GKRbRSCCkRu5au1PVtq5uADIeQySQiFARR8xEGgoxj01et8rZkC0nTZMxxuLvvIJdv20Ledd+03a9/7ylt7Vy9fAWrojEMIXitkGfItlkZjeJN9n4CkH4BZdt4ubwP3AMpG9eZ+KWovw213SqX8SoVRCCAjMVRoRCJcJhfDfZz0eZX6AwE6QoG2VIqEpaSry5YxB0H9jHwJphA3Ql+snsuRc/l+P96hkXhCHHTZGM+x9xgiKeOO75GfgjRAKc9D10s4uXzqHKlps1S+kJpEu7OpSv0tB6zTi9qjTYkViRCNmDxz729bKmUaQ8E+GBbO+9Nt/L9XTv42YH9DXV9o3cfoCsU4tbVR5IyLdb39bIxnyNkGJw1p5tTOtqpKgWeQts2qlTCK5bQjuNLUc4Y6sUOXwATQ9/Ud0opItIgFgxgBILIaJSXbJsvbdnM5nyOuGmRdx14k0wgYpgUPZfLlyzliz0LiZsmrlJ4jkOmVMIrl1HlCtp1aw7At/tZexZaI7YvWaFny5YAPCAmJE+Vinx/eJCUlPS5Lttch27DYP2S5Vw3PMhvMyMY/vVvtAbcv+YYnh4Z5h/37iFsmqyJx6m4Hj0avptuw9G6VsvVHd40Tne6Y6aelt2bHEW0z9PBRrsKQNww+FIqzRWtHTxXLPK7zMibYgISgYfmRzt3cG/XPI7pmsf1mSH+ODoKQDQcQRrSN9emEKCn568nHxHblizXh1M8eEBCSnY7Nv2Oy+pgkCVWkLtzY3xjeICjgiGeKBYau2/4wtBNXvxwvb1kIvPbY1qkpCRlGNw5Zy5BKXmpWmHM83hrMITSetok63DIUtmgtJtoZT3pnQICCHbZDkVPsSoQZJ/jcl7fAT7bf5B/aOtkkWnhASGf+PSayYm/kPevC87ybTirPK5p76SgNcfv2836XJaUkPSYJpuqFewmMmTyH9MwQ3UHr7WeaAJ6hszRQ5OQkqfKRa4YGmhckjIMHpjbQ0Urbs+OcnY8wfsiMb400MtXUq08XMyz07aJS0lOzW4chhDEhCCrFF9IpvjPcomIEHw93can+w7w9yND/HLOXL4xPMDXhvob6+YYJg/N7WkAFDPimN4cjC+nWq8+VLdF+ITFPNNEAQutAP8n2cItHV2UtebM3v2sDUW4u3sef6qUeb5SZn33PG4dG+WMWJx3hKP8uVLGYCrlVndyCWnwzx1dPFDIc3GqlSVWgIdLBW5o62SxFeAn2VFGPI8fdXTxjlCEqCGZZ1qcl2xhqRXAYWLv7nDsv+YE9UyqOPGEo6FVGtzQPgeFpqo1DxbyXDzYzxGBIPd1z2dztco1I4N8PJ7kruwYB1yHLyRTXDzY7/P71GjxSamuRJBVHp7WnJdo4dKhAe7o7CbrKb41MsS1rR1UtOaSoX5yyuPydDvfTXf4v0sz6E2fhU4f+iZtwKuLlmk9Uzdej9tkWAg2Vav8JJshJCRb7Sqv2lWWBwLc2zWfn+fG+MHoCKsCQS5Pt/N3wwNc395Jr+tOUNmZvT0sswLc0z2Pi4cGmGeaLLOCXDkyyIpAgNs6unmmXOJbI4NEheS4UJiwFMw3LL6UTFFFT0uLaz17B8tsbnDMyKX7QrAEPFUqUfR7AseFwtzQPoe4lGSV4qOxBN9Mt9FiGDw+fyHPlIpcPlzzGUkp+VQ8yQOFPL2e2wiZZ8biFJXi0VKRrY7NpUOD/GPbHKQfdSJC8GAxz6Drcm48QUUrrh8d4Q/lIgDnxJNYUlBV+rAAT8kENy1cqg8dMmr1QlAIckqxuVrBkpLVgSBBIajompMUwC7HZptt8/tSgQcLeQBiUnJLexcfisW5cLCPX+SzCCAgBI/MXcACy+LCwT5+55Mm802Lc+IJjgwGWWUFiUtJSWtsrUmYJjtch1eqVVoRrAmGqGiNISWGFEil0VpN4QZm6l6bejb7n2SvOaX4VSHHDtvmpEiUNsOg363t5qjnkZYG9xdy3Do22sgFPODSVCvHh8Psdx16PbdR5Dhas89x6JAGV6Xb2WLb7HFs9rsO3x8docs0ubOjG0MIbCFwNOwazUKxyFuVwrMsdul8TfWd2u8IRcNE43HClonw1FSydBLaiZmgnplLs4QgYRicHo1zaamf27KjeGhOjcQRaLJKsdmuEBNyQgq9JhjiI9EEVa3Zbtv8sVxq2KoC7ivkODYUIozgopY0Xx3qb5hHt2HS53mEDZP8SIZStUp0yWI6T3of0UULSa85GsOyAE1286sUd+9l8Mn/ZOiVTZhKkWpNEzIkWmmfBp8mE9y4YImezUa0v5Mjnset2VE2VitcmEyRMgxuHssQlZIFpsWrtk1JK1LS4KRIlOcrZX5TzHNnRzfvDEcoKMXnBnt5sVppAKxnfNe1dfKRaJySUnxxqI8N1SpXpNp42akSU5rTqi6xo9/K8osuZO6HTseMx2dOplyXoaeeYduNN9H/6H8QiURoiUWQSqH01DxBvLxgiZ6tWqoLoM/zeLRYYJtTZU0oTBDBb4p5XrOr2Frz0ViCs2IJjggECAlJRSu22TZHBYPsdR0uGx7k2Up5Qr1Q1wRTCK5ItfGpeJJ+z6GoNAutAAPlCoVcnnmXfIXVf38VwjQbtX6j4pvg7gXCNBqH9t71CzZ8/TKoVEgnE5hKTclOxQZfADNVS7opU0tLg52OzZcG+wgIwcdiCd4TjgKaH45luL+Y5/3hKNe2dfBEucR2p4qt4d/yWQSCvPKmVIrCd5KO1hwdDPH2UBgpJO+SFuVsjuN++mMWfebcGi/h01iI2YcutFe7izAMxl7awNOnn4mXzdKWakEqb4IQpJ44TjJtPq2p9fZyyuPuXLZGRkZjfCqeICggLiWXplr5eWc37wiH6fdcSkpxe3aMn2RHuSjZyjdTrXi+2jfHfu17/fvmzGPM8/insQz91SpGocjbf3Ybiz5zboPYEIZxSPBATUiAsm1ajn4r7/rdAxjJJGP5AlqICWMD4sWexXrWlFHXc2yNB/S7Lkv8oYSCrnGFdXuuFUKCklJEhMDz64iXqhUuHOrHEIKyUg0tkNAIox+IxLgq1cYo4AwMsvgbX2f1d7+NchykZb3uclrZNjIQoO+3D/HHsz9JsiVJ2OcK679h1mqpXhnWe689lkVRa4pK13J7XcvBtYaiUhSUh0ZT1IqbshnOHejlc4N9nBNLcl482dACUc8wpeS29jk8VS7x/oEDDGQyxI8+mlXfvhLteUjf7g+vnNQNEyg+/QxeJoMMBFC2TdfpH2Tx+eeRHRxCSdnAK6cD3Dz7M7msrPrJvGjwDuP/RFM1ZiCYb1qssAL8rKObryTT/L5U5KRwlKDfPVoTDBEXkn2uw1NzF/C5WBLTdlj6txchDWOqozsEeK0U2nXZd8657P7Aaew8+QNUd+6qCVEpll/yVcx0mnLFJ2+1Rs4EeAK5MmHUZrqhuakaZGvNx6IJLkmm2W5X+Uj/fqJCcFW6rdErOCEU5tupNr47OsIN2QwnKkHnsmXMOeO0WhPfMCbu7iy9Be15CMNg5OZbyP32IawFPVRffZXcr+6vMcGuS2zpEuacfBKlsSza1wI5G2B9mICnmxOsZY4eo8rjnmKeoBDc2j6HJ0tFCv701++KBdYEQ1ySTPNopcTO3Bjd607GjERqPYr67tffi/Gu1eTYL0yTsfX3MPC9a7E6O1HlCkYyQeQdxzcVd5q5Hz4DTyvcmcvhN24S1NXQZZjc3dFNQAheqFb4QTZTK42BXa7DZZkhvpNu46xEC/0HDmIuXjS1jJMSVSohQ6Eaxd1sGp6HME3KG16m95KvIYNBkBK3r4+5N91I9J0n1K7xI0h08UJEIIDnp/CS1z0JyrSToEyaArW1puwnVNsdm5xSjfAHsMmukPUUjufhBQKkjnzLeDvL3+3crx9g+7HvYOd7T6a6dVvtnOfV/gyD6tZt7Pv4OSANRDiMOzJC21e+TPr8zzauqYfG2JLFBDs6cGwbLUXNBN4owBOI2SaQEk1eeXwsGufEUKQWCYTAAL7V0kbST4QkIOohT+vazheK9F95Ne7wMOWXN3LwggvxcrmaXQNeNsvBCy7EHR7GiMVw+/pInPoBuq793ng3qDlHMM2GMBpRYLo53NcLeLo54fqaqtZ8LZkmLQ1crflULMHaYMjXCjEhiUHUpkIxTYzWVnSlgtXVRemlDez7xKdqdm8Y7Pv0Zym98CJmWxvuyAjRd57A3FtuGvcVk6NIo28AWoHx+UTL1fp1zOzP+jTHNH5CADbQ5Y/C9nou30m1U9W1DrQwJKVsjvSxa0m9bQ0ohRACYVlEjl1LZcNG7B07MNvbqbyyCV0uU3zqGcbWr8fs7ETl85jpNAvuXY/Z2dHQoAldICEobNnKjh/9GCtgYQKmp/WOgBRLba21qCV8bwjgaesJn+L+QDjCccEQUmvsOi/o0+nFPXsnOD+UInTEESz49X3s+8Q5lJ57HmtuFyO3/xS0xmhvbzjIBffcjTV/XsPupyRJWlM60ItbKulQNCJcz9shEewx/GTvcFV6dj8x+/i61mAimCNN7KbESStFIBxm4A9Poj13HICU4HkYiTg9v7gLq2sO3lgWI5XCSCZr312p0PWD6wgddSS47lTwTerf/8gjSKWVKSRas0cKT9yna/m8eLMAT75OAU4TQaE1aE8RjMXIvryRkT/9uXbOr+owjJoQ0il6fnEXZiqFl8mgbRv3YC9d111L8q/PrBVN06XOfti0Mxn6Hvo9Vjwq8DyU8O6TyvIeLGkvb4BoJMNvMODJa9GT2u9+79EyJNLz2PqDfxp3go3OSU0IoaOOZMG96wmuWoXZ2UnXtdeQPv+8WqyfoWjSrouQkt0//RcKO3fpSCQiSsrLVz3rQQHw9JyenyUM+dms8lwQ5iHtXx/uE2OTG62zPzYnAAdBfnSM4/7lduZ/8uONLG+8vFMN36AqFWQkckhuQBgG+de28OT71qGrttsWCJhZz73zg8N950tAaGlcW1LKFQjZnPa/3h0eD5PjOzxeV86wVteaJiYQjIR58atfY2zDywjTHB90aHKMSImMRMbNZBbwTjbLc+d/AXt0TAcDAVnyPFcjrgWEfAKMd/fu3lZBXxOXUiqt3P8twM3rxv2NIhQKoqsVnj7tIzUhWBbaccbH+Orp8OSCqbkydJwa+FyOP374LDLPv0CopcWNKSUrWl9z2nDvtqvAMP4vqHvAOK2Qe3JrNHZCizSWlbR2BBj/U5WeOZ+YfXxVKI0ZDFHN5Thw/2+ILV5EYvURCCHG+cD6QEQznadU7biUCMMgu/EVnv34uYz8+TlCra1Oi1JWTnuPnTbS//nVYFxYe6xu/LG5x7q700HPfDhmiLVjSjngPzb3JgKefiCjdlNtGFRKZVzHYdF5n2HZVy4gvmrlIamB6uAQu+64kx0334I9ktGhVNJNKmUVPf1cyRGnnpnvzfjJ2fjzv1eB/Daoe+bNS3c54pdhKU7JKYUCV9RyGPFmAZ5uRWNKVEhcrSmPjBBobaXjfe+h+4zTiS5cQHzl8pqD1JrCrt2U9x+g/9HH6H/kUYq7dutAMulZgYAZU4qyVo/kHPOcj+UOZOpYmQyq+cQTnXOvNhCXh6Q0i0rhNrHZAsSsT2S8DsAzcZGNH2mauLZNNZevMTkBi2BnB8JvxNgjIzilkhZKazMWJRQOy7DSlJXnKrjmtJG+qydjnCKAZnMQoB/vnL/aQF0M8qMmpOvDEo7WbzjYQ/Um8Qes61WgUgplOxOqvIBhYPozz45SGdD3O0rf+OHRgcN7eHrSjQ3hD3z9R1dXj+kJ//F5ehSs0JMfoNaHWTccdpGlZyVjmis9XbdnpbZKwT4Fv/aUeOhDo337AO4B42MzDK/9P5kGd0DJyzsnAAAAAElFTkSuQmCC'


# ───────────────────────── helpers ─────────────────────────
def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def fmt_short(iso):
    try:
        d = datetime.fromisoformat(iso)
    except Exception:
        return ""
    today = datetime.now().date()
    hm = d.strftime("%H:%M")
    if d.date() == today:
        return f"today {hm}"
    if (today - d.date()).days == 1:
        return f"yesterday {hm}"
    return f"{MONTHS[d.month - 1][:3]} {d.day}, {hm}"


def fmt_today():
    d = datetime.now()
    return f"{DAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}"


def set_dpi_aware():
    if not IS_WIN:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def work_area(root):
    """Screen area without the taskbar: (left, top, right, bottom)."""
    if IS_WIN:
        try:
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            r = RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)
            if r.right > r.left and r.bottom > r.top:
                return r.left, r.top, r.right, r.bottom
        except Exception:
            pass
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def system_is_light():
    if not IS_WIN:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 1
    except OSError:
        return False


def has_font(root, family):
    try:
        return tkfont.Font(root=root, family=family, size=10).actual("family").lower() == family.lower()
    except Exception:
        return False


_mutex = None


def single_instance():
    global _mutex
    if not IS_WIN:
        return True
    try:
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\DetyratNoteApp")
        return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


# ───────────────────── start with Windows ─────────────────────
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_cmd():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    w = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(w):
        exe = w
    return f'"{exe}" "{os.path.abspath(__file__)}"'


def autostart_get():
    if not IS_WIN:
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return winreg.QueryValueEx(k, APP_ID)[0]
    except OSError:
        return None


def autostart_set(on):
    if not IS_WIN:
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP_ID, 0, winreg.REG_SZ, autostart_cmd())
        else:
            try:
                winreg.DeleteValue(k, APP_ID)
            except OSError:
                pass


# ───────────────────────── storage ─────────────────────────
class Store:
    def __init__(self):
        self.data = {"tasks": [],
                     "settings": {"width": 340, "topmost": True, "collapsed": False,
                                  "show_done": True, "theme": "system",
                                  "confirm_delete": True, "text_size": "large"}}
        self.load()

    @property
    def tasks(self):
        return self.data["tasks"]

    @property
    def settings(self):
        return self.data["settings"]

    def load(self):
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                d = json.load(f)
            self.data["tasks"] = list(d.get("tasks", []))
            self.data["settings"].update(d.get("settings", {}))
        except FileNotFoundError:
            pass
        except Exception:
            try:  # corrupted file -> keep a backup and start clean
                os.replace(DATA_FILE, DATA_FILE + ".bak")
            except Exception:
                pass

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)


# ───────────────────────── app ─────────────────────────
class App:
    def __init__(self):
        set_dpi_aware()
        self.root = tk.Tk()
        self.root.withdraw()
        self.s = self.root.winfo_fpixels("1i") / 96.0
        self.store = Store()
        self.st = self.store.settings
        self.undo_stack = []
        self.wrap_labels = []
        self.ph_on = False
        self.wa = None
        self._day = datetime.now().date()
        self._sys_light = system_is_light()
        self._footer_job = None
        self._menu = None
        self._ov = None
        self.update_info = None
        self._update_dismissed = None
        self._downloading = False
        self._checking = False

        self._fonts()
        self._set_colors()
        self._icon()
        self.root.title(APP_TITLE)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", bool(self.st["topmost"]))

        self._build_all()
        self.place()
        self.root.deiconify()
        if IS_WIN:
            self.root.after(1, self._taskbar_fix)
            self.root.after(500, self._refresh_autostart)
        self.root.after(2000, self._watch)
        self.root.after(30000, self._tick)
        self.root.bind_all("<Button-1>", self._menu_outside, add="+")
        self.root.bind("<Escape>", lambda e: self.close_menu())
        if UPDATE_MANIFEST:
            self.root.after(8000, lambda: self.check_updates(False))

    # ---------- basics ----------
    def px(self, n):
        return int(round(n * self.s))

    TEXT_SIZES = {"normal": 10, "large": 11, "xlarge": 12}

    def _fonts(self):
        base = "Segoe UI" if has_font(self.root, "Segoe UI") else \
            tkfont.nametofont("TkDefaultFont").actual("family")
        semi = "Segoe UI Semibold" if has_font(self.root, "Segoe UI Semibold") else None
        self._ff = (base, semi)
        mk = lambda: tkfont.Font(family=base, size=10)
        self.f_title, self.f_sub, self.f_text, self.f_done = mk(), mk(), mk(), mk()
        self.f_meta, self.f_sec, self.f_btn = mk(), mk(), mk()
        self._apply_font_sizes()
        if has_font(self.root, "Segoe Fluent Icons"):
            self.icofam = "Segoe Fluent Icons"
        elif has_font(self.root, "Segoe MDL2 Assets"):
            self.icofam = "Segoe MDL2 Assets"
        else:
            self.icofam = None
        if self.icofam:
            self.I = dict(pin="\uE718", pinned="\uE840", more="\uE712", collapse="\uE76C",
                          expand="\uE76B", add="\uE710", delete="\uE74D", edit="\uE70F",
                          sun="\uE706", moon="\uE708")
        else:
            self.icofam = base
            self.I = dict(pin="○", pinned="●", more="⋯", collapse="›", expand="‹",
                          add="+", delete="✕", edit="✎", sun="☀", moon="☾")

    def _apply_font_sizes(self):
        base, semi = self._ff
        n = self.TEXT_SIZES.get(self.st.get("text_size"), 11)

        def strong(f, size):          # semibold if the font exists, else bold
            if semi:
                f.configure(family=semi, size=size, weight="normal")
            else:
                f.configure(family=base, size=size, weight="bold")
        strong(self.f_title, n + 6)
        strong(self.f_sec, n - 2)
        strong(self.f_btn, n - 1)
        self.f_sub.configure(family=base, size=n - 1)
        self.f_text.configure(family=base, size=n)
        self.f_done.configure(family=base, size=n, overstrike=1)
        self.f_meta.configure(family=base, size=max(8, n - 2))

    def set_text_size(self, key):
        self.st["text_size"] = key
        self.store.save()
        self._apply_font_sizes()
        self._build_all()

    def _is_light(self):
        t = self.st.get("theme", "system")
        return self._sys_light if t == "system" else t == "light"

    def _set_colors(self):
        self.C = THEMES["light" if self._is_light() else "dark"]

    def _icon(self):
        self._ico_imgs = [tk.PhotoImage(data=LOGO_64), tk.PhotoImage(data=LOGO_32)]
        size = 48 if self.s >= 1.75 else 32 if self.s >= 1.25 else 24
        self._logo_hdr = tk.PhotoImage(data={24: LOGO_24, 32: LOGO_32, 48: LOGO_48}[size])
        self._logo_big = tk.PhotoImage(data=LOGO_64 if self.s >= 1.25 else LOGO_48)
        try:
            self.root.iconphoto(True, *self._ico_imgs)
        except Exception:
            pass

    def _taskbar_fix(self):
        """Give the borderless window a taskbar button so it can always be found."""
        try:
            u = ctypes.windll.user32
            hwnd = u.GetParent(self.root.winfo_id())
            style = u.GetWindowLongW(hwnd, -20)
            style = (style & ~0x00000080) | 0x00040000  # -TOOLWINDOW +APPWINDOW
            u.SetWindowLongW(hwnd, -20, style)
            self.root.withdraw()
            self.root.deiconify()
            self.root.attributes("-topmost", bool(self.st["topmost"]))
        except Exception:
            pass

    def _refresh_autostart(self):
        """If 'Start with Windows' is on, point it at this file (e.g. after upgrading from v1)."""
        try:
            cur = autostart_get()
            if cur and cur != autostart_cmd():
                autostart_set(True)
        except Exception:
            pass

    def ibtn(self, parent, key, cmd, size=12, fg=None, hover_fg=None):
        C = self.C
        fg = fg or C["muted"]
        lbl = tk.Label(parent, text=self.I[key], font=(self.icofam, size), bg=C["panel"], fg=fg,
                       cursor="hand2", padx=self.px(9), pady=self.px(6))
        lbl._fg = fg
        lbl.bind("<Button-1>", lambda e: cmd())
        lbl.bind("<Enter>", lambda e: lbl.config(fg=hover_fg or C["text"], bg=C["btn_hover"]))
        lbl.bind("<Leave>", lambda e: lbl.config(fg=lbl._fg, bg=C["panel"]))
        return lbl

    # ---------- UI ----------
    def _build_all(self):
        self._ov = None
        self._menu = None
        for w in self.root.winfo_children():
            if not isinstance(w, tk.Menu):
                w.destroy()
        self.root.configure(bg=self.C["bg_border"])
        self._build()
        self._apply_mode()
        self.render()
        if self.update_info:
            self._show_update_banner()

    def _build(self):
        C = self.C
        P = C["panel"]
        self.outer = tk.Frame(self.root, bg=P)

        # left-edge grip for resizing
        grip = tk.Frame(self.outer, bg=P, width=self.px(5), cursor="sb_h_double_arrow")
        grip.pack(side="left", fill="y")
        grip.bind("<ButtonPress-1>", self._grip_start)
        grip.bind("<B1-Motion>", self._grip_move)
        grip.bind("<ButtonRelease-1>", self._grip_end)

        main = tk.Frame(self.outer, bg=P)
        main.pack(side="left", fill="both", expand=True)

        # header
        hdr = tk.Frame(main, bg=P)
        hdr.pack(fill="x", padx=(self.px(12), self.px(8)), pady=(self.px(12), 0))
        tk.Label(hdr, image=self._logo_hdr, bg=P).pack(side="left", padx=(0, self.px(8)))
        tk.Label(hdr, text=APP_TITLE, font=self.f_title, bg=P, fg=C["text"]).pack(side="left")
        btns = tk.Frame(hdr, bg=P)
        btns.pack(side="right")
        gap = self.px(3)
        self.btn_theme = self.ibtn(btns, "moon" if self._is_light() else "sun", self.quick_theme)
        self.btn_pin = self.ibtn(btns, "pin", self.toggle_top)
        self.btn_more = self.ibtn(btns, "more", self.show_menu)
        btn_col = self.ibtn(btns, "collapse", self.toggle_collapse)
        for b in (self.btn_theme, self.btn_pin, self.btn_more, btn_col):
            b.pack(side="left", padx=(gap, 0))
        self._pin_look()

        self.lbl_date = tk.Label(main, text=fmt_today(), font=self.f_sub, bg=P, fg=C["muted"], anchor="w")
        self.lbl_date.pack(fill="x", padx=self.px(14))

        prog = tk.Frame(main, bg=P)
        prog.pack(fill="x", padx=self.px(14), pady=(self.px(12), 0))
        self.lbl_prog = tk.Label(prog, text="", font=self.f_meta, bg=P, fg=C["muted"], anchor="w")
        self.lbl_prog.pack(fill="x")
        self.bar = tk.Canvas(prog, height=self.px(5), bg=C["track"], highlightthickness=0)
        self.bar.pack(fill="x", pady=(self.px(5), 0))
        self.bar.bind("<Configure>", lambda e: self._draw_bar())

        self.banner_slot = tk.Frame(main, bg=P)          # "update available" card goes here
        self.banner_slot.pack(fill="x")

        # new-task input + Add button
        box = tk.Frame(main, bg=C["input"], highlightthickness=1,
                       highlightbackground=C["line"], highlightcolor=C["accent"])
        box.pack(fill="x", padx=self.px(12), pady=(self.px(14), self.px(10)))
        add_btn = tk.Label(box, text="Add", font=self.f_btn, bg=C["accent"], fg=C["on_accent"],
                           cursor="hand2", padx=self.px(14), pady=self.px(6))
        add_btn.pack(side="right", padx=self.px(4), pady=self.px(4))
        add_btn.bind("<Button-1>", self.add)
        add_btn.bind("<Enter>", lambda e: add_btn.config(bg=C["accent_hover"]))
        add_btn.bind("<Leave>", lambda e: add_btn.config(bg=C["accent"]))
        self.entry = tk.Entry(box, font=self.f_text, bg=C["input"], fg=C["text"],
                              insertbackground=C["text"], relief="flat", bd=0, highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, ipady=self.px(6),
                        padx=(self.px(10), self.px(4)))
        self.entry.bind("<Return>", self.add)
        self.entry.bind("<FocusIn>", self._ph_hide)
        self.entry.bind("<FocusOut>", lambda e: self._ph_show())
        self.entry.bind("<Button-1>", lambda e: self.entry.focus_force())
        self.ph_on = False
        self._ph_show()

        # footer
        self.footer = tk.Label(main, text="", font=self.f_meta, bg=P, fg=C["faint"], anchor="w")
        self.footer.pack(side="bottom", fill="x", padx=self.px(14), pady=(self.px(4), self.px(10)))
        self.footer.bind("<Button-1>", lambda e: self.undo() if self.undo_stack else None)
        self._footer_default()

        # scrollable list
        self.canvas = tk.Canvas(main, bg=P, highlightthickness=0, yscrollincrement=self.px(20))
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=P)
        self.win_id = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_cfg)
        self.root.bind_all("<MouseWheel>", self._wheel)

        # collapsed tab
        self.tab = tk.Frame(self.root, bg=P, cursor="hand2")
        self.tabc = tk.Canvas(self.tab, bg=P, highlightthickness=0, cursor="hand2")
        self.tabc.pack(fill="both", expand=True)
        self.tabc.bind("<Configure>", lambda e: self._draw_tab())
        self.tabc.bind("<Button-1>", lambda e: self.toggle_collapse())
        self.tabc.bind("<Enter>", lambda e: self.tabc.config(bg=C["row_hover"]))
        self.tabc.bind("<Leave>", lambda e: self.tabc.config(bg=P))

        self.root.bind("<Control-n>", lambda e: self.entry.focus_force())
        self.root.bind("<Control-z>", lambda e: None if self._ov else self.undo())

    # ---------- position ----------
    def place(self):
        l, t, r, b = self.wa = work_area(self.root)
        if self.st["collapsed"]:
            w, h = self.px(34), self.px(180)
            y = t + (b - t - h) // 2
        else:
            w = min(self.px(self.st["width"]), (r - l) // 2)
            h, y = b - t, t
        self.root.geometry(f"{w}x{h}+{r - w}+{y}")

    def _apply_mode(self):
        if self.st["collapsed"]:
            self.outer.pack_forget()
            self.tab.pack(fill="both", expand=True, padx=(1, 0))
        else:
            self.tab.pack_forget()
            self.outer.pack(fill="both", expand=True, padx=(1, 0))

    def toggle_collapse(self):
        self.st["collapsed"] = not self.st["collapsed"]
        self.store.save()
        self._apply_mode()
        self.place()

    def _grip_start(self, e):
        self._gx, self._gw = e.x_root, self.root.winfo_width()

    def _grip_move(self, e):
        l, t, r, b = self.wa
        nw = max(self.px(280), min((r - l) // 2, self._gw + (self._gx - e.x_root)))
        self.root.geometry(f"{nw}x{b - t}+{r - nw}+{t}")

    def _grip_end(self, e):
        self.st["width"] = int(self.root.winfo_width() / self.s)
        self.store.save()

    def _watch(self):
        try:
            if work_area(self.root) != self.wa:
                self.place()
            if self.st["topmost"] and not self._menu and not self._ov:
                self._keep_on_top()
            if self.st.get("theme") == "system" and not self._menu:
                light = system_is_light()
                if light != self._sys_light:
                    self._sys_light = light
                    self._retheme()
        finally:
            self.root.after(2000, self._watch)

    def _keep_on_top(self):
        """Re-assert 'always on top' without activating the window (doesn't close menus)."""
        if IS_WIN:
            try:
                u = ctypes.windll.user32
                hwnd = u.GetParent(self.root.winfo_id())
                u.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0013)
                return
            except Exception:
                pass
        self.root.attributes("-topmost", True)

    def _tick(self):
        try:
            self.lbl_date.config(text=fmt_today())
            if datetime.now().date() != self._day:
                self._day = datetime.now().date()
                self.render()
        finally:
            self.root.after(30000, self._tick)

    # ---------- theme ----------
    def set_theme(self, name):
        self.st["theme"] = name
        self.store.save()
        self._sys_light = system_is_light()
        self._retheme()

    def quick_theme(self):
        self.set_theme("dark" if self._is_light() else "light")

    def _retheme(self):
        self._set_colors()
        self._build_all()

    # ---------- scroll / wrap ----------
    def _on_canvas_cfg(self, e):
        self.canvas.itemconfigure(self.win_id, width=e.width)
        self._update_wrap(e.width)

    def _update_wrap(self, w=None):
        w = w or self.canvas.winfo_width()
        n = self.TEXT_SIZES.get(self.st.get("text_size"), 11)
        wl = max(80, w - self.px(24) - self.px(42) - self.px(80 + (n - 10) * 6))
        for lbl in self.wrap_labels:
            try:
                lbl.configure(wraplength=wl)
            except tk.TclError:
                pass

    def _wheel(self, e):
        if self.inner.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll((-2 if e.delta > 0 else 2), "units")

    # ---------- placeholder ----------
    def _ph_show(self):
        if not self.entry.get():
            self.entry.insert(0, PLACEHOLDER)
            self.entry.config(fg=self.C["faint"])
            self.ph_on = True

    def _ph_hide(self, _=None):
        if self.ph_on:
            self.entry.delete(0, "end")
            self.entry.config(fg=self.C["text"])
            self.ph_on = False

    # ---------- actions ----------
    def add(self, _=None):
        v = self.entry.get().strip()
        if not v or self.ph_on:
            self.entry.focus_force()
            return
        self.store.tasks.append({"id": uuid.uuid4().hex, "text": v, "done": False,
                                 "created": now_iso(), "done_at": None})
        self.store.save()
        self.entry.delete(0, "end")
        self.render()
        self.root.after_idle(self._scroll_to_last_pending)

    def _scroll_to_last_pending(self):
        w = getattr(self, "_last_pending_row", None)
        if not w or not w.winfo_exists():
            return
        self.root.update_idletasks()
        total = max(1, self.inner.winfo_height())
        y = w.winfo_y() + w.winfo_height()
        top, bot = self.canvas.yview()
        if y / total > bot:
            self.canvas.yview_moveto(max(0, (y - self.canvas.winfo_height()) / total))

    def toggle(self, t):
        t["done"] = not t["done"]
        t["done_at"] = now_iso() if t["done"] else None
        self.store.save()
        self.render()

    def delete(self, t):
        if self.st.get("confirm_delete", True):
            text = t["text"] if len(t["text"]) <= 90 else t["text"][:87] + "…"
            self.confirm("Delete this task?", f"“{text}”", lambda: self._do_delete(t))
        else:
            self._do_delete(t)

    def _do_delete(self, t):
        if t not in self.store.tasks:
            return
        i = self.store.tasks.index(t)
        self.undo_stack = [(i, t)]
        self.store.tasks.pop(i)
        self.store.save()
        self.render()
        self._footer_undo("Task deleted")

    def clear_done(self):
        n = sum(1 for t in self.store.tasks if t["done"])
        if not n:
            return
        if self.st.get("confirm_delete", True):
            what = "1 completed task" if n == 1 else f"all {n} completed tasks"
            self.confirm("Clear completed?", f"This will delete {what}.", self._do_clear_done)
        else:
            self._do_clear_done()

    def _do_clear_done(self):
        removed = [(i, t) for i, t in enumerate(self.store.tasks) if t["done"]]
        if not removed:
            return
        self.undo_stack = removed
        self.store.data["tasks"] = [t for t in self.store.tasks if not t["done"]]
        self.store.save()
        self.render()
        self._footer_undo(f"Cleared {len(removed)} completed")

    def undo(self):
        if not self.undo_stack:
            return
        for i, t in sorted(self.undo_stack, key=lambda x: x[0]):
            self.store.tasks.insert(min(i, len(self.store.tasks)), t)
        self.undo_stack = []
        self.store.save()
        self.render()
        self._footer_default()

    # ---------- in-panel dialogs (overlay) ----------
    # Drawn inside the main window instead of a separate window, so they can never
    # slip behind the always-on-top panel.
    def _overlay(self):
        """Returns (card, close) — or (None, None) if a dialog is already open."""
        if getattr(self, "_ov", None) is not None and self._ov.winfo_exists():
            return None, None
        self.close_menu()
        if self.st["collapsed"]:
            self.toggle_collapse()
        C = self.C
        ov = tk.Frame(self.root, bg=C["scrim"])
        ov.place(x=0, y=0, relwidth=1, relheight=1)
        self._ov = ov
        card = tk.Frame(ov, bg=C["row"], highlightthickness=1, highlightbackground=C["line"])
        card.place(relx=0.5, rely=0.36, anchor="center", width=self.root.winfo_width() - self.px(28))

        def close(_=None):
            if self._ov is not None:
                self._ov.destroy()
                self._ov = None
            try:
                self.entry.focus_set()
            except tk.TclError:
                pass
        ov.bind("<Button-1>", close)      # click outside the card = cancel
        ov.bind("<Escape>", close)
        self.root.after(1, lambda: (self.root.focus_force(), ov.focus_set()))
        return card, close

    def _dlg_button(self, parent, text, bg, fg, hover, cmd):
        b = tk.Label(parent, text=text, font=self.f_btn, bg=bg, fg=fg, cursor="hand2",
                     padx=self.px(18), pady=self.px(8))
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.config(bg=hover))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def confirm(self, title, message, on_yes):
        card, close = self._overlay()
        if card is None:
            return
        C = self.C
        pad = self.px(20)
        tk.Label(card, text=title, font=self.f_btn, bg=C["row"], fg=C["text"], anchor="w"
                 ).pack(fill="x", padx=pad, pady=(pad, self.px(6)))
        tk.Label(card, text=message, font=self.f_text, bg=C["row"], fg=C["muted"], anchor="w",
                 justify="left", wraplength=self.root.winfo_width() - self.px(28) - 2 * pad
                 ).pack(fill="x", padx=pad)
        btns = tk.Frame(card, bg=C["row"])
        btns.pack(fill="x", padx=pad, pady=(self.px(20), pad))

        def yes(_=None):
            close()
            on_yes()
        self._dlg_button(btns, "Yes, delete", C["danger"], "#ffffff", C["danger_hover"], yes
                         ).pack(side="right")
        self._dlg_button(btns, "No", C["btn_hover"], C["text"], C["line"], close
                         ).pack(side="right", padx=(0, self.px(8)))
        self._ov.bind("<Return>", yes)

    def show_about(self):
        card, close = self._overlay()
        if card is None:
            return
        C = self.C
        tk.Label(card, image=self._logo_big, bg=C["row"]).pack(pady=(self.px(24), self.px(10)))
        tk.Label(card, text=APP_TITLE, font=self.f_title, bg=C["row"], fg=C["text"]).pack()
        tk.Label(card, text=f"Version {VERSION}", font=self.f_meta, bg=C["row"], fg=C["muted"]).pack()
        tk.Frame(card, bg=C["line"], height=1).pack(fill="x", padx=self.px(40), pady=self.px(14))
        tk.Label(card, text="Designed & built by", font=self.f_meta, bg=C["row"], fg=C["muted"]).pack()
        tk.Label(card, text=AUTHOR, font=self.f_btn, bg=C["row"], fg=C["accent"]).pack(pady=(self.px(2), 0))
        tk.Label(card, text=f"© {datetime.now().year} {AUTHOR}  ·  All rights reserved",
                 font=self.f_meta, bg=C["row"], fg=C["faint"]).pack(pady=(self.px(10), 0))
        self._dlg_button(card, "Close", C["accent"], C["on_accent"], C["accent_hover"], close
                         ).pack(pady=(self.px(18), self.px(22)))
        self._ov.bind("<Return>", close)

    # ---------- updates ----------
    @staticmethod
    def _vt(v):
        return tuple(int(x) for x in re.findall(r"\d+", str(v))) or (0,)

    def _footer_msg(self, text, ms=6000):
        self.footer.config(text=text, fg=self.C["accent"], cursor="")
        if self._footer_job:
            self.root.after_cancel(self._footer_job)
        self._footer_job = self.root.after(ms, self._footer_default)

    def check_updates(self, manual=False):
        if not manual:                                   # next automatic check in 6 hours
            self.root.after(6 * 3600 * 1000, lambda: self.check_updates(False))
        if not UPDATE_MANIFEST:
            if manual:
                self._footer_msg("Updates are not set up in this build (see repo.txt)")
            return
        if self._checking or self._downloading:
            return
        self._checking = True
        if manual:
            self._footer_msg("Checking for updates…", 20000)
        q = queue.Queue()

        def work():
            try:
                req = urllib.request.Request(UPDATE_MANIFEST, headers={"User-Agent": f"Tasks/{VERSION}"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    q.put(("ok", json.loads(r.read().decode("utf-8"))))
            except Exception as ex:
                q.put(("err", str(ex)))
        threading.Thread(target=work, daemon=True).start()

        def poll():
            try:
                kind, data = q.get_nowait()
            except queue.Empty:
                self.root.after(200, poll)
                return
            self._checking = False
            newer = kind == "ok" and self._vt(data.get("version")) > self._vt(VERSION)
            if newer and (manual or data.get("version") != self._update_dismissed):
                self.update_info = data
                self._show_update_banner()
                if manual:
                    self._footer_default()
            elif manual:
                self._footer_msg(f"You're up to date  ·  v{VERSION}" if kind == "ok"
                                 else "Couldn't check for updates — are you online?")
        poll()

    def _show_update_banner(self):
        info = self.update_info
        if not info or not getattr(self, "banner_slot", None) or not self.banner_slot.winfo_exists():
            return
        for w in self.banner_slot.winfo_children():
            w.destroy()
        C = self.C
        A = C["accent"]
        card = tk.Frame(self.banner_slot, bg=A)
        card.pack(fill="x", padx=self.px(12), pady=(self.px(12), 0))
        inner = tk.Frame(card, bg=A)
        inner.pack(fill="x", padx=self.px(14), pady=self.px(12))
        tk.Label(inner, text=f"Update available  ·  v{info.get('version')}", font=self.f_btn,
                 bg=A, fg="#ffffff", anchor="w").pack(fill="x")
        notes = [n.strip("-• ").strip() for n in str(info.get("notes") or "").splitlines() if n.strip()]
        if notes:
            tk.Label(inner, text=notes[0][:140], font=self.f_meta, bg=A, fg="#ffe1e1", anchor="w",
                     justify="left", wraplength=self.root.winfo_width() - self.px(70)).pack(fill="x")
        row = tk.Frame(inner, bg=A)
        row.pack(fill="x", pady=(self.px(10), 0))
        self.upd_label = tk.Label(row, text="", font=self.f_sec, bg=A, fg="#ffffff", anchor="w")
        if self._downloading:
            self.upd_label.config(text="Downloading…")
            self.upd_label.pack(side="left")
            return
        now = tk.Label(row, text="Update now", font=self.f_btn, bg="#ffffff", fg=A, cursor="hand2",
                       padx=self.px(14), pady=self.px(5))
        now.pack(side="left")
        now.bind("<Button-1>", lambda e: self.start_update())
        later = tk.Label(row, text="Later", font=self.f_btn, bg=A, fg="#ffffff", cursor="hand2",
                         padx=self.px(12), pady=self.px(5))
        later.pack(side="left", padx=(self.px(6), 0))
        later.bind("<Button-1>", lambda e: self._dismiss_update())

    def _dismiss_update(self):
        if self.update_info:
            self._update_dismissed = self.update_info.get("version")
        self.update_info = None
        for w in self.banner_slot.winfo_children():
            w.destroy()

    def _upd_text(self, text):
        lbl = getattr(self, "upd_label", None)
        if lbl is not None and lbl.winfo_exists():
            lbl.config(text=text)

    def start_update(self):
        info = self.update_info or {}
        url, sha = info.get("url"), str(info.get("sha256") or "").lower()
        if self._downloading or not url or not sha:
            return
        self._downloading = True
        self._show_update_banner()
        dest = os.path.join(tempfile.gettempdir(), f"Tasks-Setup-{info.get('version')}.exe")
        q = queue.Queue()

        def work():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": f"Tasks/{VERSION}"})
                h = hashlib.sha256()
                with urllib.request.urlopen(req, timeout=30) as r, open(dest + ".part", "wb") as f:
                    total, got = int(r.headers.get("Content-Length") or 0), 0
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        h.update(chunk)
                        got += len(chunk)
                        q.put(("p", got / total if total else 0))
                if h.hexdigest().lower() != sha:
                    os.remove(dest + ".part")
                    raise ValueError("download was damaged (checksum mismatch)")
                os.replace(dest + ".part", dest)
                q.put(("ok", dest))
            except Exception as ex:
                q.put(("err", str(ex)))
        threading.Thread(target=work, daemon=True).start()

        def poll():
            last = None
            try:
                while True:
                    last = q.get_nowait()
                    if last[0] != "p":
                        break
            except queue.Empty:
                pass
            if last is None or last[0] == "p":
                if last:
                    self._upd_text(f"Downloading…  {int(last[1] * 100)}%")
                self.root.after(100, poll)
                return
            if last[0] == "ok":
                self._upd_text("Starting the installer…")
                self.root.after(200, lambda: self._run_installer(last[1]))
            else:
                self._downloading = False
                self._show_update_banner()
                self._footer_msg("Update failed: " + last[1][:80], 9000)
        poll()

    def _run_installer(self, path):
        ok = False
        if IS_WIN:
            # ShellExecute shows the UAC prompt (installer needs admin for Program Files)
            r = ctypes.windll.shell32.ShellExecuteW(None, "open", path, "--update", None, 1)
            ok = r > 32
        if ok:
            self.root.after(300, self.root.destroy)        # the installer restarts Tasks when done
        else:
            self._downloading = False
            self._show_update_banner()
            self._footer_msg("Update cancelled", 6000)

    def _footer_default(self):
        self.footer.config(text="Enter: add  ·  Double-click: edit  ·  Ctrl+Z: undo",
                           fg=self.C["faint"], cursor="")

    def _footer_undo(self, msg):
        self.footer.config(text=f"{msg}  —  click here to undo", fg=self.C["accent"], cursor="hand2")
        if self._footer_job:
            self.root.after_cancel(self._footer_job)
        self._footer_job = self.root.after(7000, self._footer_default)

    def toggle_top(self):
        self.st["topmost"] = not self.st["topmost"]
        self.root.attributes("-topmost", bool(self.st["topmost"]))
        self.store.save()
        self._pin_look()

    def _pin_look(self):
        on = bool(self.st["topmost"])
        self.btn_pin.config(text=self.I["pinned" if on else "pin"])
        self.btn_pin._fg = self.C["accent"] if on else self.C["muted"]
        self.btn_pin.config(fg=self.btn_pin._fg)

    def toggle_done_section(self):
        self.st["show_done"] = not self.st["show_done"]
        self.store.save()
        self.render()

    # ---------- settings menu (drawn inside the panel, can't vanish) ----------
    def close_menu(self):
        if self._menu is not None:
            try:
                self._menu.destroy()
            except tk.TclError:
                pass
            self._menu = None

    def _menu_outside(self, e):
        if self._menu is None:
            return
        w = str(e.widget)
        if w.startswith(str(self._menu)) or w.startswith(str(self.btn_more)):
            return
        self.close_menu()

    def _hover(self, widgets, normal, hover):
        first = str(widgets[0])

        def inside(e):
            try:
                w = self.root.winfo_containing(e.x_root, e.y_root)
            except Exception:
                return False
            return w is not None and (str(w) == first or str(w).startswith(first + "."))

        def on(e):
            for w in widgets:
                w.config(bg=hover)

        def off(e):
            if not inside(e):
                for w in widgets:
                    w.config(bg=normal)
        for w in widgets:
            w.bind("<Enter>", on, add="+")
            w.bind("<Leave>", off, add="+")

    def show_menu(self):
        if self._menu is not None:
            return self.close_menu()
        if self._ov is not None:
            return
        self.root.update_idletasks()                  # layout must be final (e.g. right after a theme switch)
        C = self.C
        P = C["row"]
        m = tk.Frame(self.root, bg=P, highlightthickness=1, highlightbackground=C["line"])
        self._menu = m
        width = min(self.px(290), self.root.winfo_width() - self.px(20))
        b = self.btn_more
        y, w = b.winfo_height() + self.px(4), b
        while w is not self.root:                     # position relative to the panel
            y += w.winfo_y()
            w = w.master
        m.place(x=self.root.winfo_width() - width - self.px(10), y=y, width=width)
        pad = self.px(14)

        def section(text, top=12):
            tk.Label(m, text=text, font=self.f_sec, bg=P, fg=C["faint"], anchor="w").pack(
                fill="x", padx=pad, pady=(self.px(top), self.px(6)))

        def segmented(options, current, cmd):
            f = tk.Frame(m, bg=C["track"])
            f.pack(fill="x", padx=pad)
            for val, lbl in options:
                on = val == current
                x = tk.Label(f, text=lbl, font=self.f_sec if on else self.f_meta, cursor="hand2",
                             bg=C["accent"] if on else C["track"],
                             fg=C["on_accent"] if on else C["muted"], pady=self.px(6))
                x.pack(side="left", fill="x", expand=True, padx=self.px(2), pady=self.px(2))
                if not on:
                    x.bind("<Enter>", lambda e, x=x: x.config(fg=C["text"]))
                    x.bind("<Leave>", lambda e, x=x: x.config(fg=C["muted"]))
                    x.bind("<Button-1>", lambda e, v=val: cmd(v))

        def switch(text, value, cmd):
            row = tk.Frame(m, bg=P, cursor="hand2")
            row.pack(fill="x")
            lbl = tk.Label(row, text=text, font=self.f_sub, bg=P, fg=C["text"], anchor="w", cursor="hand2")
            lbl.pack(side="left", padx=pad, pady=self.px(8))
            W, H = self.px(36), self.px(20)
            sw = tk.Canvas(row, width=W, height=H, bg=P, highlightthickness=0, cursor="hand2")
            sw.pack(side="right", padx=pad)
            state = [bool(value)]

            def draw():
                sw.delete("all")
                col = C["accent"] if state[0] else C["faint"]
                sw.create_oval(0, 0, H, H, fill=col, outline=col)
                sw.create_oval(W - H, 0, W, H, fill=col, outline=col)
                sw.create_rectangle(H / 2, 0, W - H / 2, H, fill=col, outline=col)
                k = self.px(3)
                x = (W - H) if state[0] else 0
                sw.create_oval(x + k, k, x + H - k, H - k, fill="#ffffff", outline="")

            def click(_=None):
                state[0] = not state[0]
                draw()
                cmd(state[0])
            draw()
            for w in (row, lbl, sw):
                w.bind("<Button-1>", click)
            self._hover([row, lbl, sw], P, C["row_hover"])

        def action(text, cmd, fg=None, enabled=True, hint=None):
            row = tk.Frame(m, bg=P, cursor="hand2" if enabled else "arrow")
            row.pack(fill="x")
            lbl = tk.Label(row, text=text, font=self.f_sub, bg=P, anchor="w",
                           fg=(fg or C["text"]) if enabled else C["faint"])
            lbl.pack(side="left", padx=pad, pady=self.px(8))
            ws = [row, lbl]
            if hint:
                h = tk.Label(row, text=hint, font=self.f_meta, bg=P, fg=C["faint"])
                h.pack(side="right", padx=pad)
                ws.append(h)
            if enabled:
                def go(_=None):
                    self.close_menu()
                    cmd()
                for w in ws:
                    w.bind("<Button-1>", go)
                self._hover(ws, P, C["row_hover"])

        def divider():
            tk.Frame(m, bg=C["line"], height=1).pack(fill="x", pady=self.px(6))

        def reopen(fn):
            def run(v):
                fn(v)
                self.root.after(10, self.show_menu)
            return run

        section("THEME", top=14)
        segmented((("system", "Auto"), ("light", "Light"), ("dark", "Dark")),
                  self.st.get("theme", "system"), reopen(self.set_theme))
        section("TEXT SIZE")
        segmented((("normal", "Normal"), ("large", "Large"), ("xlarge", "Extra large")),
                  self.st.get("text_size", "large"), reopen(self.set_text_size))
        section("BEHAVIOUR", top=14)
        switch("Always on top", self.st["topmost"], lambda v: self.toggle_top())
        if IS_WIN:
            switch("Start with Windows", bool(autostart_get()), self._set_auto)
        switch("Ask before deleting", self.st.get("confirm_delete", True),
               lambda v: self._set_setting("confirm_delete", v))
        divider()
        action("Check for updates", lambda: self.check_updates(True), hint=f"v{VERSION}")
        action("Clear completed", self.clear_done, enabled=any(t["done"] for t in self.store.tasks))
        if IS_WIN:
            action("Open data folder", self._open_data)
        action(f"About {APP_TITLE}", self.show_about)
        divider()
        action("Exit", self.root.destroy, fg=C["danger"])
        tk.Frame(m, bg=P, height=self.px(6)).pack()
        m.lift()

    def _set_setting(self, key, value):
        self.st[key] = value
        self.store.save()

    def _set_auto(self, on):
        try:
            autostart_set(on)
        except Exception:
            pass

    def _open_data(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.startfile(DATA_DIR)

    # ---------- drawing ----------
    @staticmethod
    def _mix(c1, c2, t):
        a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
        return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def _draw_bar(self):
        c = self.bar
        c.delete("all")
        n = len(self.store.tasks)
        d = sum(1 for t in self.store.tasks if t["done"])
        if not (n and d):
            return
        width = int(c.winfo_width() * d / n)
        h = self.px(5)
        if d == n:
            c.create_rectangle(0, 0, width, h, fill=self.C["done"], width=0)
            return
        step = 3
        for x in range(0, width, step):
            col = self._mix(self.C["accent"], self.C["accent2"], x / max(1, c.winfo_width()))
            c.create_rectangle(x, 0, min(x + step, width), h, fill=col, width=0)

    def _draw_tab(self):
        c = self.tabc
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        n = sum(1 for t in self.store.tasks if not t["done"])
        c.create_image(w / 2, self.px(18), image=self._logo_hdr)
        c.create_text(w / 2, h / 2 + self.px(10), text=f"TASKS  ·  {n}",
                      angle=90, font=self.f_sec, fill=self.C["text"])

    def _update_header(self):
        n = len(self.store.tasks)
        d = sum(1 for t in self.store.tasks if t["done"])
        self.lbl_prog.config(text=f"{d} of {n} completed" if n else "No tasks yet")
        self._draw_bar()
        self._draw_tab()

    def _draw_check(self, cv, done, hover=False):
        C = self.C
        cv.delete("all")
        s, p = self.px(22), self.px(2)
        if done:
            cv.create_oval(p, p, s - p, s - p, fill=C["done"], outline=C["done"])
            cv.create_line(self.px(7), self.px(11.5), self.px(10), self.px(14.5),
                           self.px(15.5), self.px(8), fill="#ffffff",
                           width=max(2, self.px(2)), capstyle="round", joinstyle="round")
        else:
            cv.create_oval(p, p, s - p, s - p, outline=C["accent"] if hover else C["muted"],
                           width=max(1, self.px(1.6)))

    def _section(self, title, n, done_section=False):
        C = self.C
        P = C["panel"]
        f = tk.Frame(self.inner, bg=P)
        f.pack(fill="x", padx=self.px(14), pady=(self.px(12), self.px(6)))
        if done_section:
            arrow = "▾" if self.st["show_done"] else "▸"
            lbl = tk.Label(f, text=f"{arrow}  {title}  {n}", font=self.f_sec, bg=P,
                           fg=C["muted"], cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e: self.toggle_done_section())
            clr = tk.Label(f, text="Clear", font=self.f_sec, bg=P, fg=C["muted"], cursor="hand2",
                           padx=self.px(8), pady=self.px(3))
            clr.pack(side="right")
            clr.bind("<Button-1>", lambda e: self.clear_done())
            clr.bind("<Enter>", lambda e: clr.config(fg=C["danger"], bg=C["btn_hover"]))
            clr.bind("<Leave>", lambda e: clr.config(fg=C["muted"], bg=P))
        else:
            tk.Label(f, text=f"{title}  {n}", font=self.f_sec, bg=P, fg=C["muted"]).pack(side="left")

    def _row(self, t):
        C = self.C
        R = C["row"]
        done = t["done"]
        row = tk.Frame(self.inner, bg=R, highlightthickness=1, highlightbackground=C["line"])
        row.pack(fill="x", padx=self.px(12), pady=(0, self.px(7)))

        cb = tk.Canvas(row, width=self.px(22), height=self.px(22), bg=R,
                       highlightthickness=0, cursor="hand2")
        cb.pack(side="left", anchor="n", padx=(self.px(10), self.px(8)), pady=self.px(10))
        self._draw_check(cb, done)

        acts = tk.Frame(row, bg=R)
        acts.pack(side="right", anchor="n", padx=(0, self.px(4)), pady=self.px(6))
        be = tk.Label(acts, text=self.I["edit"], font=(self.icofam, 11), bg=R, fg=R,
                      cursor="hand2", padx=self.px(7), pady=self.px(5))
        bd = tk.Label(acts, text=self.I["delete"], font=(self.icofam, 11), bg=R, fg=R,
                      cursor="hand2", padx=self.px(7), pady=self.px(5))
        be.pack(side="left", padx=(0, self.px(2)))
        bd.pack(side="left")

        body = tk.Frame(row, bg=R)
        body.pack(side="left", fill="both", expand=True, pady=self.px(9))
        lbl = tk.Label(body, text=t["text"], font=self.f_done if done else self.f_text,
                       fg=C["muted"] if done else C["text"], bg=R, justify="left", anchor="w")
        lbl.pack(fill="x")
        meta_txt = ("Completed " + fmt_short(t.get("done_at") or "")) if done \
            else ("Added " + fmt_short(t.get("created") or ""))
        meta = tk.Label(body, text=meta_txt, font=self.f_meta, fg=C["faint"], bg=R, anchor="w")
        meta.pack(fill="x", pady=(self.px(2), 0))
        self.wrap_labels.append(lbl)
        # wrap exactly at the width the text area really gets
        body.bind("<Configure>", lambda e: lbl.configure(wraplength=max(60, e.width - self.px(4))), add="+")

        widgets = [row, cb, acts, be, bd, body, lbl, meta]
        rowpath = str(row)

        def inside(e):
            try:
                w = self.root.winfo_containing(e.x_root, e.y_root)
            except Exception:
                return False
            return w is not None and (str(w) == rowpath or str(w).startswith(rowpath + "."))

        def enter(e):
            for w in widgets:
                w.configure(bg=C["row_hover"])
            be.configure(fg=C["muted"])
            bd.configure(fg=C["muted"])
            self._draw_check(cb, done, hover=True)

        def leave(e):
            if inside(e):
                return
            for w in widgets:
                w.configure(bg=R)
            be.configure(fg=R)
            bd.configure(fg=R)
            self._draw_check(cb, done)

        for w in widgets:
            w.bind("<Enter>", enter, add="+")
            w.bind("<Leave>", leave, add="+")
        for b, col in ((be, C["accent"]), (bd, C["danger"])):
            b.bind("<Enter>", lambda e, b=b, col=col: b.configure(fg=col, bg=C["btn_hover"]), add="+")
            b.bind("<Leave>", lambda e, b=b: b.configure(fg=C["muted"], bg=C["row_hover"])
                   if inside(e) else None, add="+")

        cb.bind("<Button-1>", lambda e: self.toggle(t))
        bd.bind("<Button-1>", lambda e: self.delete(t))
        be.bind("<Button-1>", lambda e: self._edit(t, lbl, meta, body))
        for w in (lbl, meta, body):
            w.bind("<Double-Button-1>", lambda e: self._edit(t, lbl, meta, body))
        return row

    def _edit(self, t, lbl, meta, body):
        if not lbl.winfo_ismapped():
            return
        C = self.C
        lbl.pack_forget()
        e = tk.Entry(body, font=self.f_text, bg=C["input"], fg=C["text"],
                     insertbackground=C["text"], relief="flat", highlightthickness=1,
                     highlightcolor=C["accent"], highlightbackground=C["line"])
        e.insert(0, t["text"])
        e.pack(fill="x", before=meta, ipady=self.px(4))
        e.focus_force()
        e.select_range(0, "end")
        finished = [False]

        def finish(save):
            if finished[0]:
                return
            finished[0] = True
            if save:
                v = e.get().strip()
                if v and v != t["text"]:
                    t["text"] = v
                    self.store.save()
            self.root.after_idle(self.render)

        e.bind("<Return>", lambda _: finish(True))
        e.bind("<Escape>", lambda _: finish(False))
        e.bind("<FocusOut>", lambda _: finish(True))

    def render(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.wrap_labels = []
        self._last_pending_row = None
        tasks = self.store.tasks
        pending = [t for t in tasks if not t["done"]]
        done = sorted((t for t in tasks if t["done"]),
                      key=lambda t: t.get("done_at") or "", reverse=True)

        self._section("TO DO", len(pending))
        if not pending:
            tk.Label(self.inner, text="Nothing here — add a task above.",
                     font=self.f_sub, bg=self.C["panel"], fg=self.C["faint"], anchor="w"
                     ).pack(fill="x", padx=self.px(16), pady=(0, self.px(6)))
        for t in pending:
            self._last_pending_row = self._row(t)

        if done:
            self._section("COMPLETED", len(done), done_section=True)
            if self.st["show_done"]:
                for t in done:
                    self._row(t)

        self._update_header()
        self.root.after_idle(self._update_wrap)
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            self.canvas.yview_moveto(0)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not single_instance():
        if IS_WIN:
            ctypes.windll.user32.MessageBoxW(None, "Tasks is already running.", APP_TITLE, 0x40)
        sys.exit(0)
    App().run()
