# Product Requirements Document (PRD)
# Chatbot Kerajaan Agency — Telegram

**Version:** 3.0 (Revisi — Conversational Chatbot, Prompt Templates + Knowledge Base)
**Status:** Draft
**Platform:** Telegram
**AI Model:** gpt-oss (20b / 120b via Groq atau OpenRouter, OpenAI-compatible API)
**Knowledge Base:** Company Profile + Recruitment Kerajaan Agency
**Target User:** KOL / Creator / Affiliate
**Development Team:** 2 orang / 2 device
**Base Project:** Revisi dari repo existing `chatbot-nasikotak-ai-engineer` (bukan rewrite proyek baru)

---

## 1. Perubahan Utama dari Versi Sebelumnya

Versi ini mengubah konsep interaksi Telegram dari **command-based bot** menjadi **conversational chatbot**.

### Perubahan

- Tidak menggunakan command seperti `/start`, `/about`, `/join`, `/faq`, atau `/help` sebagai alur utama.
- User cukup **langsung mengirim pesan/chat biasa** di Telegram.
- Semua pertanyaan diproses melalui pipeline AI existing.
- Respons chatbot ditentukan berdasarkan **`prompt_templates.py` + RAG/Knowledge Base**.
- Knowledge Base menjadi sumber informasi utama dan prompt templates menjadi pengatur perilaku, gaya, batasan, dan aturan respons chatbot.
- Tidak menggunakan menu berbasis command untuk memaksa user memilih topik.
- CTA pendaftaran hanya diberikan ketika konteks percakapan menunjukkan user tertarik untuk bergabung.
- Pekerjaan Person A ditempatkan pada branch **`aisma`**.
- Pekerjaan Person B ditempatkan pada branch **`rehan`**.
- Website dan registration backend tetap berada di Phase 2.
- Codebase existing tetap digunakan dan hanya disesuaikan dengan kebutuhan Kerajaan Agency.

### Prinsip Utama

```text
USER CHAT
   ↓
TELEGRAM BOT
   ↓
PIPELINE
   ↓
RAG / KNOWLEDGE BASE
   ↓
PROMPT TEMPLATES
   ↓
LLM
   ↓
NATURAL CHAT RESPONSE
```

---

## 2. Overview

### 2.1 Product Name

**Kerajaan Agency Telegram Chatbot**

### 2.2 Background

Kerajaan Agency merupakan rebranding dari **Majapahit Agency**. Chatbot ini adalah pengembangan ulang dari chatbot lama pada project `chatbot-nasikotak-ai-engineer`.

Knowledge Base lama yang berisi informasi F&B tidak digunakan sebagai sumber jawaban. Sistem diarahkan untuk menggunakan Knowledge Base baru yang berisi company profile dan recruitment Kerajaan Agency.

> **PRODUCT + CREATOR + CONTENT + DISTRIBUTION = COMMERCE**

### 2.3 Product Description

Chatbot adalah AI assistant resmi Kerajaan Agency di Telegram yang memungkinkan calon KOL, Creator, dan Affiliate untuk bertanya secara bebas menggunakan bahasa natural.

User tidak perlu mengetahui command tertentu. User cukup mengirim pertanyaan seperti:

```text
Apa itu Kerajaan Agency?
```

atau:

```text
Aku tertarik jadi affiliate, gimana caranya?
```

Bot kemudian mencari informasi yang relevan dari Knowledge Base dan menghasilkan jawaban berdasarkan aturan pada `prompt_templates.py`.

---

## 3. Product Objective

### 3.1 Primary Objective

Membangun chatbot Telegram sebagai **digital frontliner dan lead-generation channel** Kerajaan Agency yang dapat:

1. Memahami pertanyaan user dalam bahasa natural.
2. Menjelaskan Kerajaan Agency berdasarkan Knowledge Base.
3. Menjawab pertanyaan mengenai ekosistem creator.
4. Menjelaskan peluang dan benefit creator.
5. Mengarahkan user yang menunjukkan minat untuk bergabung ke link pendaftaran.
6. Memberikan pengalaman chat yang natural tanpa bergantung pada command Telegram.

### 3.2 Secondary Objectives

1. Mengurangi pertanyaan berulang kepada tim agency.
2. Memberikan informasi 24/7 melalui Telegram.
3. Menjaga konsistensi informasi.
4. Menghindari hallucination atau informasi yang tidak didukung Knowledge Base.
5. Menggunakan kembali pipeline, RAG, LLM service, conversation manager, dan prompt templates dari project existing.

---

## 4. Target User

### 4.1 Primary User — KOL / Creator / Affiliate

User yang:

- Memiliki audience.
- Mampu dan konsisten membuat konten.
- Mau belajar.
- Mau mencoba produk.
- Berorientasi pada hasil.
- Mampu membangun trust dengan audience.

Jumlah followers bukan satu-satunya indikator.

### 4.2 Secondary User

Producer, maklon, brand owner, distributor, dan supplier dapat memperoleh informasi yang tersedia di Knowledge Base, tetapi chatbot MVP tetap dioptimalkan untuk KOL / Creator / Affiliate.

---

## 5. Product Scope

### 5.1 In Scope

#### A. Conversational Company Profile

User dapat langsung bertanya mengenai:

- Kerajaan Agency.
- Visi dan misi.
- Business ecosystem.
- Product engine.
- Creator ecosystem.
- Content engine.
- Distribution/channel.
- Product Lab.
- Content Factory.
- Technology & AI.
- Prinsip kerja.
- Komitmen terhadap creator.
- Alasan bergabung dengan Kerajaan Agency.

Tidak ada command khusus untuk membuka topik tersebut.

Contoh:

```text
User:
Kerajaan Agency itu apa?

Bot:
[Jawaban berdasarkan RAG + prompt_templates.py]
```

---

#### B. Conversational KOL / Creator Recruitment

User dapat bertanya secara bebas mengenai:

- Cara bergabung.
- Cara menjadi KOL/Creator.
- Cara menjadi affiliate.
- Benefit creator.
- Training.
- Community.
- Product/sample.
- Content support.
- Affiliate opportunity.
- Commission, apabila informasinya tersedia di Knowledge Base.

Jika user menunjukkan intent untuk bergabung, chatbot dapat memberikan CTA pendaftaran.

Contoh:

```text
User:
Aku mau jadi affiliate Kerajaan Agency.

Bot:
[Penjelasan singkat berdasarkan Knowledge Base]

Kalau kamu tertarik bergabung, kamu bisa melakukan
pendaftaran melalui link resmi yang tersedia.
```

CTA tidak muncul pada setiap percakapan. CTA muncul berdasarkan konteks dan intent user.

---

#### C. Natural Conversation

Bot harus dapat menangani variasi bahasa natural, termasuk:

```text
apa itu kerajaan agency
kerajaan agency ngapain?
aku mau join
gimana cara daftar?
ada komisi gak?
jadi creator dapat apa?
aku tertarik jadi affiliate
boleh jelasin benefitnya?
```

User tidak perlu menggunakan format atau command tertentu.

---

#### D. Contextual Conversation

Bot dapat mempertahankan konteks percakapan melalui `conversation_manager.py`.

Contoh:

```text
User:
Apa benefit jadi creator?

Bot:
[Menjelaskan benefit]

User:
Kalau affiliate gimana?

Bot:
[Menjawab pertanyaan affiliate dengan mempertimbangkan
konteks percakapan sebelumnya]
```

---

### 5.2 Out of Scope — MVP

- Website pendaftaran KOL.
- Form registrasi di Telegram.
- Backend API registrasi.
- Database KOL.
- Marketplace.
- Transaksi produk langsung di Telegram.
- Pembayaran commission.
- Dashboard KOL.
- Product matching otomatis.
- Creator matching otomatis.
- Analisis performa KOL.
- Live commission tracking.
- Customer service order.
- Integrasi marketplace.
- Database 30.000 KOL.
- Automatic approval / commission calculation.

---

## 6. Knowledge Base

### 6.1 Source

Knowledge Base berasal dari:

- Company Profile Kerajaan Agency.
- Konten recruitment KOL/Creator.

### 6.2 Struktur

```text
knowledge_base/
├── company/
│   └── company_profile.md
└── recruitment/
    ├── pendaftaran_kol.md
    └── promosi_kol.md
```

Folder lama:

```text
addons/
delivery/
faq/
products/
promotion/
```

dikeluarkan dari proses ingestion RAG untuk chatbot Kerajaan Agency.

Folder lama tidak harus langsung dihapus secara fisik. Cukup pastikan folder tersebut tidak ikut di-ingest oleh RAG.

---

### 6.3 Knowledge Restriction

Knowledge Base adalah **sumber fakta utama chatbot**.

Chatbot:

- Wajib menggunakan context dari Knowledge Base.
- Tidak boleh mengarang informasi.
- Tidak boleh mengisi kekosongan informasi dengan asumsi.
- Harus menyatakan informasi belum tersedia apabila informasi yang diminta tidak terdapat di Knowledge Base.

Chatbot tidak boleh mengarang:

- Nominal commission.
- Gaji KOL.
- Guaranteed income.
- Guaranteed sales.
- Jumlah sample.
- Produk yang sedang tersedia.
- Syarat program yang belum tercantum.
- Data performa.
- Kebijakan internal.
- Informasi lain yang tidak tersedia pada Knowledge Base.

---

## 7. AI Architecture

```text
                         ┌─────────────────────┐
                         │      TELEGRAM       │
                         │     USER / CHAT     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  telegram_bot.py    │
                         │ Natural Chat Handler │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    pipeline.py      │
                         │ Existing Orchestrator│
                         └──────────┬──────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     │              │              │
                     ▼              ▼              ▼
              conversation_   rag_service.py   prompt_templates.py
              manager.py       Retrieval        AI Rules / Behavior
                     │              │              │
                     │              ▼              │
                     │       knowledge_base/      │
                     │       company/             │
                     │       recruitment/         │
                     │              │              │
                     └──────────────┼──────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │   llm_service.py    │
                         │      gpt-oss         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Telegram Reply    │
                         │   Natural Language   │
                         └─────────────────────┘
```

### 7.1 Architecture Principle

Telegram hanya berfungsi sebagai **interface/chat channel**.

Logika AI tidak ditempatkan seluruhnya di `telegram_bot.py`.

`telegram_bot.py` bertanggung jawab untuk:

- Menerima pesan.
- Mengambil identitas/chat ID user.
- Mengirim pesan ke pipeline.
- Mengirim hasil pipeline kembali ke Telegram.
- Menangani error dasar Telegram.

Sedangkan:

- `rag_service.py` → retrieval Knowledge Base.
- `prompt_templates.py` → aturan dan perilaku AI.
- `conversation_manager.py` → context dan conversation state.
- `pipeline.py` → orkestrasi proses.
- `llm_service.py` → komunikasi dengan LLM.

---

## 8. Prompt Templates

### 8.1 Prinsip

`prompt_templates.py` menjadi pusat pengaturan perilaku chatbot.

Prompt harus mengatur:

1. Identitas chatbot.
2. Tujuan chatbot.
3. Bahasa dan gaya komunikasi.
4. Penggunaan Knowledge Base.
5. Anti-hallucination.
6. Penanganan pertanyaan di luar Knowledge Base.
7. Promotion/CTA berdasarkan intent.
8. Cara mempertahankan konteks percakapan.

### 8.2 Baseline System Prompt

```text
You are the official AI assistant of Kerajaan Agency.

Your role is to help users understand Kerajaan Agency,
its creator ecosystem, opportunities, and recruitment
information.

Conversation Policy:
- Users communicate naturally through chat.
- Do not require Telegram commands.
- Answer the user's actual question directly.
- Maintain conversation context when relevant.
- Use the provided Knowledge Base as the source of factual
  information.

Knowledge Policy:
- Use only information supported by the provided Knowledge Base.
- Do not invent information.
- Do not guess missing information.
- Do not make up commission amounts.
- Do not promise income, sales, or viral content.
- Do not claim guaranteed results.
- Do not invent products, programs, requirements, or policies.

Recruitment Policy:
- When the user shows genuine interest in joining as a KOL,
  Creator, or Affiliate, explain the relevant opportunity
  based on the Knowledge Base.
- Provide the registration CTA when appropriate.
- Do not repeatedly promote registration when the user is
  only asking an informational question.

Fallback Policy:
- If the requested information is not available in the
  Knowledge Base, clearly state that the information is
  currently unavailable.
- Do not fill missing information with assumptions.
```

Prompt di atas merupakan baseline. Implementasi final tetap mengikuti struktur dan mekanisme `prompt_templates.py` pada codebase existing.

---

## 9. Telegram User Flow

### 9.1 Conversational Flow

Tidak ada flow wajib berbasis command.

```text
User membuka Telegram
        │
        ▼
User mengirim chat
        │
        ▼
telegram_bot.py menerima pesan
        │
        ▼
pipeline.py
        │
        ├── conversation_manager.py
        │
        ├── rag_service.py
        │        │
        │        └── Knowledge Base
        │
        └── prompt_templates.py
                 │
                 ▼
             LLM / gpt-oss
                 │
                 ▼
          Natural Response
                 │
                 ▼
              Telegram
```

### 9.2 First Message

Ketika user pertama kali mengirim pesan, chatbot dapat memberikan respons berdasarkan pesan tersebut.

Contoh:

```text
User:
Halo, aku mau tahu tentang Kerajaan Agency.

Bot:
Halo! 👋
Tentu, aku bisa bantu menjelaskan tentang Kerajaan Agency...
```

Tidak diperlukan:

```text
/start
```

untuk memulai percakapan.

---

## 10. Main Features

### 10.1 Natural Language Chat

User dapat bertanya tanpa command.

Contoh:

```text
Apa itu Kerajaan Agency?
```

```text
Benefit jadi creator apa aja?
```

```text
Cara menghasilkan uang sebagai creator gimana?
```

```text
Aku tertarik jadi affiliate.
```

```text
Kalau mau join gimana?
```

---

### 10.2 Creator Benefit

Informasi benefit diambil dari Knowledge Base.

Contoh format respons:

```text
🎁 Sebagai creator di ekosistem Kerajaan Agency,
kamu berpotensi mendapatkan akses ke:

• Product
• Sample sesuai program
• Content Kit
• Affiliate Link
• Commission
• Training
• Community
• Performance System
```

Detail hanya boleh diberikan jika didukung Knowledge Base.

---

### 10.3 Creator Monetization

Konsep monetisasi dapat dijelaskan berdasarkan Knowledge Base:

```text
PRODUCT → CONTENT → TRAFFIC → CLICK → PURCHASE → COMMISSION
```

Bot tidak boleh mengubah alur tersebut menjadi janji penghasilan.

---

### 10.4 Contextual Promotion

Promotion tidak menggunakan command khusus.

Trigger berasal dari **intent dan konteks percakapan**.

Contoh intent:

```text
mau join
mau gabung
jadi KOL
jadi creator
jadi affiliate
cara daftar
tertarik
mau menghasilkan
cara dapat commission
```

Contoh:

```text
User:
Aku mau jadi affiliate.

Bot:
Kamu bisa mulai dengan bergabung ke ekosistem creator
Kerajaan Agency. [Penjelasan berdasarkan KB]

Kalau kamu tertarik bergabung, kamu bisa melakukan
pendaftaran melalui link yang tersedia.
```

CTA diberikan secara kontekstual, bukan sebagai menu utama.

---

## 11. Registration Flow — MVP

Pendaftaran belum dilakukan di dalam Telegram.

```text
User menunjukkan minat
        │
        ▼
Bot menjelaskan opportunity
        │
        ▼
Bot memberikan CTA/link pendaftaran
        │
        ▼
User membuka link
        │
        ▼
Selesai
```

Placeholder:

```text
https://kerajaanagency.com/daftar-kol
```

> URL di atas masih placeholder dan harus diganti ketika website resmi tersedia.

Tidak ada:

- Form registrasi Telegram.
- Penyimpanan data registrasi.
- Database KOL untuk MVP.

---

## 12. Fallback Handling

### 12.1 Information Not Available

```text
Maaf, informasi tersebut belum tersedia
di Knowledge Base Kerajaan Agency.
```

Bot tidak boleh membuat jawaban sendiri untuk menutup kekosongan informasi.

### 12.2 Out of Scope

```text
Aku dapat membantu menjelaskan mengenai
Kerajaan Agency, ekosistem creator, peluang
KOL/affiliate, dan proses bergabung.

Silakan tanyakan apa yang ingin kamu ketahui.
```

Respons tetap harus disesuaikan dengan konteks percakapan.

---

## 13. Technology Stack

- **Platform:** Telegram.
- **Backend:** existing project stack.
- **AI:** gpt-oss-20b/120b melalui Groq atau OpenRouter.
- **LLM Integration:** `llm_service.py`.
- **RAG:** `rag_service.py`.
- **Orchestration:** `pipeline.py`.
- **Conversation:** `conversation_manager.py`.
- **Prompt:** `prompt_templates.py`.
- **Knowledge Base:** Markdown.
- **Vector Store:** gunakan vector store existing; jika belum tersedia, gunakan FAISS sebagai opsi ringan.
- **Deployment:** Docker & docker-compose existing.
- **Telegram Library:** `python-telegram-bot` atau library Telegram yang kompatibel dengan struktur project existing.

Tidak perlu membuat FastAPI baru hanya untuk Telegram.

---

## 14. Project Structure

```text
chatbot-nasikotak-ai-engineer/
│
├── knowledge_base/
│   ├── company/
│   │   └── company_profile.md
│   └── recruitment/
│       ├── pendaftaran_kol.md
│       └── promosi_kol.md
│
├── notebooks/
│
├── src/
│   ├── data/
│   ├── config.py
│   ├── conversation_manager.py
│   ├── database.py
│   ├── lead_manager.py
│   ├── llm_service.py
│   ├── outlet_service.py
│   ├── pipeline.py
│   ├── prompt_templates.py
│   ├── rag_service.py
│   ├── sales_engine.py
│   └── telegram_bot.py
│
├── static/
├── app.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

### 14.1 File yang Perlu Dievaluasi

Komponen F&B lama tidak boleh tetap memengaruhi chatbot.

Evaluasi:

- `lead_manager.py`
- `outlet_service.py`
- `sales_engine.py`
- logic F&B pada `conversation_manager.py`
- logic F&B pada `prompt_templates.py`
- ingestion folder lama pada `rag_service.py`

Komponen yang tidak relevan dapat dinonaktifkan atau disesuaikan, tetapi tidak perlu melakukan rewrite besar terhadap project.

---

## 15. Git Strategy

Branch utama:

```text
main
develop
```

Branch pekerjaan:

```text
aisma
rehan
```

### 15.1 Person A — Branch `aisma`

Fokus pada **Knowledge Base + Prompt + Conversation Logic**.

Tugas:

- Restructure `knowledge_base/`.
- Rebrand content Majapahit → Kerajaan Agency.
- Memasukkan company profile ke KB.
- Memasukkan recruitment content ke KB.
- Exclude folder lama dari ingestion.
- Update `rag_service.py`.
- Rebuild/test vector index.
- Update `prompt_templates.py`.
- Menyesuaikan system prompt.
- Menghapus/menyesuaikan logic prompt lama yang berkaitan dengan F&B.
- Update `conversation_manager.py`.
- Menyesuaikan intent dan context conversation untuk Kerajaan Agency.
- Memastikan promotion/CTA berjalan berdasarkan konteks, bukan command.

**Branch:**

```text
aisma
```

---

### 15.2 Person B — Branch `rehan`

Fokus pada **LLM Integration + Telegram Integration**.

Tugas:

- Update `config.py`.
- Update `llm_service.py`.
- Integrasi gpt-oss melalui Groq/OpenRouter.
- Test koneksi LLM.
- Membuat `telegram_bot.py`.
- Membuat handler untuk **pesan/chat biasa**.
- Menghubungkan Telegram → `pipeline.py`.
- Menghubungkan output pipeline → Telegram.
- Menangani error Telegram.
- Setup bot melalui BotFather.
- Menggunakan polling untuk development/testing.
- Memastikan bot tidak bergantung pada `/start`, `/about`, `/join`, `/faq`, atau `/help`.

**Branch:**

```text
rehan
```

---

## 16. Team Integration

Setelah masing-masing pekerjaan selesai:

```text
                    develop
                   /       \
                  /         \
             aisma           rehan
               │               │
               │               │
        KB + Prompt       Telegram + LLM
               │               │
               └───────┬───────┘
                       │
                       ▼
                 Integration Test
                       │
                       ▼
                  develop
                       │
                       ▼
                     main
```

### Integration Rule

Kedua branch tidak boleh saling mengubah bagian pekerjaan secara sembarangan.

Jika terjadi perubahan pada file yang sama, lakukan sinkronisasi sebelum merge.

File yang berpotensi conflict:

- `config.py`
- `conversation_manager.py`
- `pipeline.py`
- `prompt_templates.py`
- `rag_service.py`
- `requirements.txt`
- `app.py`

---

## 17. Recommended Development Order

```text
STEP 1
Setup repository dan branch:
- aisma
- rehan

STEP 2
Person A:
Rebuild Knowledge Base

STEP 3
Person A:
Update RAG + prompt_templates + conversation_manager

STEP 4
Person B:
Integrasi gpt-oss

STEP 5
Person B:
Membuat telegram_bot.py
untuk natural chat

STEP 6
Person A + B:
Integration test

STEP 7
Test anti-hallucination

STEP 8
Test Telegram end-to-end

STEP 9
Merge ke develop

STEP 10
Deploy
```

Prioritas:

```text
1. Knowledge Base akurat
2. Prompt behavior konsisten
3. RAG relevan
4. LLM stabil
5. Telegram stabil
6. Promotion/CTA sesuai konteks
```

---

## 18. Testing

### 18.1 Natural Chat Test

Minimal chatbot harus dapat menjawab:

```text
1. Apa itu Kerajaan Agency?
2. Kerajaan Agency itu agency apa?
3. Apa benefit menjadi creator?
4. Bagaimana cara creator menghasilkan uang?
5. Apakah harus punya banyak followers?
6. Apakah creator harus membeli stok?
7. Apakah ada training?
8. Apakah ada community?
9. Apa itu affiliate?
10. Bagaimana cara join?
```

### 18.2 Anti-Hallucination Test

Pertanyaan berikut digunakan untuk memastikan bot tidak mengarang:

```text
11. Berapa commission?
12. Berapa gaji KOL?
13. Apakah penghasilan dijamin?
14. Produk apa yang tersedia sekarang?
15. Apakah saya pasti mendapatkan sample?
16. Siapa KOL terbesar di Kerajaan Agency?
```

Jika data tidak tersedia di Knowledge Base, chatbot harus menyatakan informasi tersebut belum tersedia.

### 18.3 Conversation Context Test

```text
User:
Apa benefit jadi creator?

Bot:
[Jawaban]

User:
Kalau affiliate?

Bot:
[Jawaban affiliate berdasarkan konteks sebelumnya]
```

### 18.4 Promotion Test

```text
User:
Aku tertarik jadi affiliate.

Expected:
Bot menjelaskan opportunity + CTA pendaftaran
jika didukung Knowledge Base.
```

Sebaliknya:

```text
User:
Apa itu Kerajaan Agency?

Expected:
Bot menjawab pertanyaan.
Tidak wajib langsung memberikan CTA pendaftaran.
```

### 18.5 Command Independence Test

Pesan berikut harus dapat diproses sebagai chat biasa:

```text
Halo
Apa itu Kerajaan Agency?
Mau join
Cara daftar gimana?
Ada benefit apa?
```

Tidak ada ketergantungan terhadap command Telegram.

---

## 19. Acceptance Criteria

### Telegram

- [ ] Bot dapat menerima pesan teks biasa.
- [ ] User tidak wajib menggunakan command untuk berinteraksi.
- [ ] Pesan Telegram diteruskan ke pipeline.
- [ ] Pipeline menghasilkan response yang dikirim kembali ke Telegram.
- [ ] Conversation context dapat dipertahankan.
- [ ] Error Telegram ditangani dengan baik.
- [ ] Tidak ada ketergantungan pada `/start`, `/about`, `/join`, `/faq`, atau `/help`.

### AI

- [ ] Prompt templates Kerajaan Agency sudah diterapkan.
- [ ] RAG mengambil context yang relevan.
- [ ] Jawaban berdasarkan Knowledge Base.
- [ ] Tidak ada hallucination terhadap data yang tidak tersedia.
- [ ] Fallback bekerja.
- [ ] gpt-oss bekerja stabil.
- [ ] Promotion CTA muncul secara kontekstual.
- [ ] Bot tidak menjanjikan income/commission/sales yang tidak didukung KB.

### Knowledge Base

- [ ] Company profile sudah dikonversi ke Kerajaan Agency.
- [ ] Recruitment content sudah masuk KB.
- [ ] Folder F&B lama tidak ikut ingestion.
- [ ] Vector index berhasil dibuat.
- [ ] Retrieval menghasilkan context relevan.

### Git & Integration

- [ ] Pekerjaan Person A berada di branch `aisma`.
- [ ] Pekerjaan Person B berada di branch `rehan`.
- [ ] Kedua branch dapat diintegrasikan ke `develop`.
- [ ] Tidak ada secret di repository.
- [ ] Docker/docker-compose existing tetap dapat menjalankan sistem.

---

## 20. Security Requirements

- Semua secret disimpan di `.env`.
- `TELEGRAM_BOT_TOKEN` tidak boleh di-commit.
- API key provider LLM tidak boleh di-commit.
- `.gitignore` harus mencakup:

```text
.env
.venv/
__pycache__/
*.pyc
```

---

## 21. Success Metrics — MVP

Karena website dan registrasi belum menjadi bagian MVP, metrik utama:

- Jumlah user Telegram.
- Jumlah conversation.
- Jumlah pertanyaan terkait KOL/Creator/Affiliate.
- Jumlah user yang menunjukkan intent join.
- Jumlah klik link/CTA pendaftaran.
- Persentase pertanyaan yang dapat dijawab berdasarkan Knowledge Base.
- Tingkat keberhasilan fallback untuk informasi yang tidak tersedia.

---

## 22. Future Development

### Phase 2 — Website & Registration

- Landing page.
- `/daftar-kol` atau `/join-kol`.
- Registration form.
- Backend API.
- Database KOL.
- Success page.
- Mobile responsive.
- Sinkronisasi Telegram → Website → API → Database.

### Phase 3 — KOL Management

- KOL onboarding.
- Status KOL.
- Automated notification.
- Admin dashboard.
- FAQ management.
- Analytics.

### Phase 4 — AI & Creator Intelligence

- Creator matching.
- Product recommendation.
- Creator scoring.
- Performance analytics.
- Commission tracking.

### Phase 5 — AI Content Assistant

- Hook generator.
- Script generator.
- Caption generator.
- AI product matching.
- Performance dashboard.

---

## 23. Final Product Principle

Chatbot Kerajaan Agency MVP harus terasa seperti **percakapan dengan AI assistant**, bukan seperti bot command.

```text
BUKAN:

/start
/about
/join
/faq

MELAINKAN:

User:
"Kerajaan Agency itu apa?"

Bot:
[Jawaban berdasarkan Knowledge Base]

User:
"Aku tertarik jadi affiliate."

Bot:
[Jawaban berdasarkan Knowledge Base
+ CTA jika sesuai konteks]
```

### Source of Truth

```text
KNOWLEDGE BASE
      +
PROMPT TEMPLATES
      +
CONVERSATION CONTEXT
      ↓
      LLM
      ↓
NATURAL TELEGRAM CHAT
```

**Prinsip utama:**

> User cukup chat. Bot memahami konteks. Jawaban harus berdasarkan Prompt Templates dan Knowledge Base. Bot tidak boleh mengarang informasi.
