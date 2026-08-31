<div dir="rtl">

# ⚡ هه‌واڵ — پنل مدیریت تانل چند‌هسته‌ای

> کنترل‌پنلی سبک برای ساخت، پایش و مدیریت تانل بین نودهای ایران و خارج.

[![License: MIT](https://img.shields.io/badge/License-MIT-2563eb.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?logo=docker&logoColor=white)](docker-compose.yml)
[![Cores](https://img.shields.io/badge/Cores-Hawal%20%7C%20Backhaul%20%7C%20Paqet-0f766e)](#هستهها-و-انتخاب-صحیح)

**هه‌واڵ** در کردی یعنی «دوست و همراه». Hawal پیکربندی تانل‌ها را در پنل نگه می‌دارد و ایجنت‌های سبک، آن را روی سرورها همگام و اجرا می‌کنند.

[English documentation](README.md)

---

## امکانات

- ساخت و ویرایش تانل با چند پورت فوروارد از پنل وب
- افزودن نودهای ایران و خارج با دستور نصب تولیدشده از پنل
- سه هستهٔ قابل انتخاب: **Hawal Stealth Core**، **Backhaul** و **Paqet**
- وضعیت زندهٔ نودها، CPU/RAM، تست Ping و بررسی سلامت
- شمارش واقعی مصرف Paqet از raw-table سرور مقصد، شامل سربار KCP
- سرویس‌های Systemd برای پنل و ایجنت و Docker Compose برای پنل
- SQLite داخلی، بدون وابستگی به Redis یا دیتابیس خارجی

## معماری

```text
 مرورگر
    │
    ▼
┌──────────────────────┐     همگام‌سازی تنظیمات      ┌──────────────────────┐
│ پنل Hawal :9090      │◄───────────────────────────►│ ایجنت نودها          │
│ نودها، تانل‌ها، آمار │                              │ /opt/hawal/agent.py  │
└──────────────────────┘                              └──────────┬───────────┘
                                                                  │
       Hawal Stealth Core  |  Backhaul Mux  |  Paqet Raw TCP + KCP
                                                                  │
       پورت ورودی ایران ◄────────────── تانل ──────────────► سرویس خارج
```

## هسته‌ها و انتخاب صحیح

| هسته | مناسب برای | انتقال | نکته |
|---|---|---|---|
| ⚡ **Hawal Stealth Core** | شروع ساده و استفادهٔ عمومی | `stealth` | هستهٔ اختصاصی Hawal با padding و `nodelay` |
| 🚀 **Backhaul** | تانل‌های multiplex استاندارد | `ws`، `tcp`، `tcpmux`، `tls` | پورت هسته باید از پورت‌های فوروارد جدا باشد |
| 🛡️ **Paqet** | مسیرهای raw-packet/KCP | `kcp` | به root، NIC مناسب و firewall نیاز دارد؛ برای سناریوهای پیشرفته |

### توصیه

1. برای شروع، **Hawal Stealth Core** را انتخاب کنید.
2. برای انتقال‌های استاندارد و multiplex، **Backhaul** مناسب است.
3. **Paqet** را فقط در صورت آشنایی با raw socket و عیب‌یابی firewall انتخاب کنید. برای پورت هستهٔ آن از پورت غیرمتعارف و اختصاصی مثل `3107` یا `9999` استفاده کنید؛ **80 و 443 پورت هستهٔ Paqet نباشند**.

## پیش‌نیازها

- Linux دارای systemd و دسترسی `root`
- Python 3، `curl` و `tar`
- یک پورت آزاد برای پنل (پیش‌فرض `9090`)
- یک پورت آزاد و یکتا برای هستهٔ هر تانل
- دسترسی ایجنت‌ها به پنل و دسترسی دو نود به پورت هسته

> پورت پنل را روی اینترنت بدون کنترل دسترسی رها نکنید؛ با firewall، VPN یا reverse proxy از آن محافظت کنید.

## نصب سریع

### ۱. نصب پنل

روی سرور پنل اجرا کنید:

```bash
curl -fsSL https://raw.githubusercontent.com/T4wroot/hawal/master/install-panel.sh | bash
```

پورت دلخواه:

```bash
curl -fsSL https://raw.githubusercontent.com/T4wroot/hawal/master/install-panel.sh | bash -s -- --port 9090
```

پس از نصب، پنل در `http://IP-پنل:9090` در دسترس است.

### ۲. افزودن نود

1. در **مدیریت نودها**، نود ایران و خارج را اضافه کنید.
2. دستور تولیدشده را روی همان نود اجرا کنید.
3. منتظر وضعیت `Online` بمانید.

نمونهٔ دستور نصب نود:

```bash
curl -fsSL "http://PANEL_IP:9090/install?token=NODE_TOKEN&role=kharej&name=Germany" | bash
```

### ۳. ساخت تانل

نودها، هسته، پورت هسته و پورت‌های فوروارد را انتخاب کنید. قالب پورت فوروارد:

```text
443=127.0.0.1:443
8443=127.0.0.1:8443
```

نمونه:

```text
نام:              iran-to-germany-443
هسته:             Hawal Stealth Core
پورت هسته:        3107
پورت فوروارد:     443=127.0.0.1:443
```

`3107` پورت ارتباط هسته است و `443` پورت قابل‌استفادهٔ کاربر؛ این دو را یکی انتخاب نکنید.

## Paqet: آمار و نکات عملی

Paqet از raw TCP packet و KCP استفاده می‌کند. به همین علت `ss` و `/proc/PID/io` برای حجم آن معتبر نیستند. Hawal بایت‌های raw-table سرور مقصد را گزارش می‌کند؛ بنابراین حجم نمایش‌داده‌شده، مصرف واقعی شبکه **به‌همراه سربار KCP** است.

- به root و `iptables` نیاز دارد.
- قوانین `NOTRACK` و جلوگیری از RST فقط روی پورت هستهٔ نود سرور اعمال می‌شوند.
- پورت فوروارد کلاینت باید TCP عادی و tracked باقی بماند.
- با شروع ایجنت، قوانین ضروری Paqet دوباره برقرار می‌شوند.

## عملیات و عیب‌یابی

```bash
# وضعیت پنل
systemctl status hawal-panel --no-pager

# وضعیت و لاگ ایجنت روی هر نود
systemctl status hawal-agent --no-pager
journalctl -u hawal-agent -n 100 --no-pager

# لاگ یک تانل Paqet
tail -f /opt/hawal/logs/TUNNEL_ID.log

# پورت‌های در حال شنود
ss -lntup
```

برای نود offline، ابتدا دسترسی به پنل، token، firewall و سرویس `hawal-agent` را بررسی کنید. برای Paqet مطمئن شوید پورت هسته روی نود خارج اختصاصی است و قوانین raw-table وجود دارند.

## Docker Compose

```bash
git clone https://github.com/T4wroot/hawal.git
cd hawal
docker compose up -d --build
docker compose logs -f hawal-panel
```

پنل در حالت Docker از شبکهٔ میزبان استفاده می‌کند و روی پورت 9090 در دسترس است.

## امنیت و استفادهٔ مسئولانه

- tokenهای نود محرمانه‌اند؛ آن‌ها را در Issue، لاگ یا اسکرین‌شات منتشر نکنید.
- پنل عمومی را پشت TLS و کنترل دسترسی شبکه قرار دهید.
- قبل از باز کردن پورت‌ها، firewall و سرویس مقصد را بررسی کنید.
- مسئولیت رعایت قوانین، شرایط دیتاسنتر و سیاست شبکه با استفاده‌کننده است.

## مشارکت و لایسنس

Issue و Pull Request خوش‌آمد است. در گزارش باگ، نسخه، هسته، نقش نودها و لاگ پاک‌سازی‌شده از token را اضافه کنید.

منتشرشده تحت [MIT License](LICENSE) © 2026 [T4wroot](https://github.com/T4wroot) و مشارکت‌کنندگان Hawal.

</div>
