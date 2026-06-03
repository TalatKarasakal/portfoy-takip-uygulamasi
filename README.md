# portfoy-takip-uygulaması

Kişisel yatırım portföyü (BIST hisseleri ve TEFAS fonları) takip ve analiz
masaüstü uygulaması. Python + PySide6 (MVVM) ile geliştirilmiştir.

## Yapay Zeka Özellikleri

Uygulamaya, tamamen **ücretsiz** çalışan bir yapay zeka asistanı eklendi.
Asistan sol menüdeki **"Asistan"** sekmesinden kullanılır.

### Sağlayıcı seçenekleri (her ikisi de ücretsiz)

Ayarlar > **Yapay Zeka** bölümünden seçilir:

- **Ollama** — Kendi makinenizde çalışan yerel modeller (llama3.1, qwen2.5,
  gemma2 vb.). İnternet gerektirmez, tamamen ücretsiz ve gizlidir.
  Kurulum: https://ollama.com (`ollama pull llama3.1`).
- **Google Gemini** — Ücretsiz katmanı olan bulut modeli. Yalnızca bir API
  anahtarı gerekir: https://aistudio.google.com/app/apikey

### Özellikler

1. **Portföy Asistanı (sohbet)** — Portföyünüz hakkında doğal dilde soru sorun.
2. **Otomatik Portföy Özeti** — Güncel durumun kısa Türkçe özeti.
3. **Doğal Dil ile İşlem Girişi** — "Dün 100 THYAO aldım 280 liradan" → işlem kaydı.
4. **Akıllı Risk Analizi** — Konsantrasyon ve çeşitlendirme uyarıları (LLM'siz, anında).
5. **Teknik Analiz** — SMA, EMA, RSI, MACD ve trend sinyali (yerel hesaplama).
6. **Anomali Tespiti** — Olağandışı fiyat hareketlerini yakalar (yerel hesaplama).
7. **Haber Duygu Analizi** — Bir varlık hakkındaki güncel haberlerin duygu skoru.
8. **Hedef Bazlı Öneri** — Risk + teknik göstergelere dayalı iyileştirme önerileri.

> Teknik analiz, anomali tespiti ve risk analizi tamamen yerel ve LLM'siz
> çalışır; sağlayıcı seçilmemiş olsa bile kullanılabilir.
