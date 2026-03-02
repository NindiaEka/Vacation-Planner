General Instructions
1. Create a git code repository on either github/gitlab, and share the instructions to access
you solution
2. Please do not plagiarize/copy-paste any publicly available solution. You are allowed to
use code-assist tools and research. Please give reference to the tools/resources you
used.
3. As a solution, create a Solutions document that explains your approach and steps.

ASSIGNMENT
Design and implement a proof-of-concept solution for building a planner that can
autonomously plan a vacation for you and also make necessary bookings, if the
user has provided payment information and given such permissions.
You can make suitable assumptions to implement the PoC. For example, assume
that the planner has access to your calendar, preferences, etc.
Make sure that you use as much open source GenAI technologies as suitable in
your solution.
Submission Checklist:
○ Solution document explaining the problem, your approach/high-level architecture,
techstack
○ Repository link
○ Hosted solution/ demo video
○ Add one section in your solution report where you list all vulnerabilities and risks
you can identify in your design choices. For each risk, (1) describe the potential
attack scenario, (2) assess the likelihood and impact, (3) propose mitigation
strategies considering budget constraints, and (4) explain how you would monitor
for these risks in production.

Penjelasan 
1. General Instructions & Requirements (Poin 1 - 6)
Poin ini berfokus pada cara kamu mengelola proyek dan etika pengembangan:

    1. Git Repository: Kamu wajib membuat repositori kode di GitHub atau GitLab. Sertakan instruksi yang jelas (biasanya di README.md) tentang cara mengakses dan menjalankan solusimu.

    2. Anti-Plagiarism: Dilarang keras menyalin solusi publik secara mentah-mentah.

    3. Research & Tools: Kamu diperbolehkan menggunakan code-assist tools (seperti GitHub Copilot) dan melakukan riset.

    4. Reference: Kamu wajib memberikan referensi atau mencantumkan daftar alat/sumber daya yang kamu gunakan selama pengerjaan.

    5. Solutions Document: Kamu harus membuat dokumen (PDF/Word) yang menjelaskan pendekatan teknis dan langkah-langkah yang kamu ambil.

    6. Approach Explanation: Dokumen tersebut harus menceritakan alur pikirmu dalam menyelesaikan masalah.

2. Assignment Scope (Poin 7 - 10)
Poin ini mendefinisikan apa yang harus dibangun oleh sistemmu:

    7. Proof-of-Concept (PoC): Implementasikan solusi untuk membangun planner liburan.

    8. Autonomous Planning: Sistem harus bisa merencanakan liburan secara mandiri (otonom).

    9. Booking Execution: Sistem harus bisa melakukan pemesanan (booking) jika user memberikan informasi pembayaran dan izin (permissions).

    10. Assumptions: Kamu diperbolehkan membuat asumsi logis, seperti asisten sudah memiliki akses ke kalender dan preferensi pengguna.

    11. Open Source GenAI: Kamu diwajibkan menggunakan sebanyak mungkin teknologi Open Source GenAI (contoh: Llama 3 via Groq/Ollama) dalam solusimu.

3. Submission Checklist (Poin 11 - 14)
Apa saja yang harus kamu kumpulkan:

    12. Solution Report: Dokumen yang menjelaskan masalah, arsitektur tingkat tinggi (high-level architecture), dan tech stack yang digunakan.

    13. Repository Link: Tautan aktif ke GitHub/GitLab kamu.

    14. Demo: Solusi yang sudah di-host (seperti di Streamlit Cloud) atau rekaman video demonstrasi.

4. Keamanan & Risiko (Poin 15 - 16)
Ini adalah bagian yang paling krusial dalam laporanmu dan sering dianggap sebagai "ujian" sebenarnya bagi seorang AI Engineer:

    15. Vulnerabilities Section: Tambahkan satu bagian khusus di laporan solusi yang mendaftarkan semua kerentanan dan risiko dari pilihan desainmu.

    16. Risk Detail Breakdown: Untuk setiap risiko yang teridentifikasi, kamu wajib menjelaskan:


        (1) Attack Scenario: Deskripsikan bagaimana potensi serangan terjadi.


        (2) Likelihood & Impact: Nilai seberapa besar kemungkinan terjadinya dan seberapa parah dampaknya.


        (3) Mitigation Strategy: Usulkan strategi pencegahan dengan mempertimbangkan batasan biaya (budget constraints).


        (4) Production Monitoring: Jelaskan bagaimana cara kamu memantau risiko ini saat aplikasi sudah berjalan secara live.