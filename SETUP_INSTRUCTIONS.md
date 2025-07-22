# Site Crawler MCP - Kurulum ve Test Talimatları

## Kurulum Adımları

### 1. Projeyi Hazırlama

```bash
# Proje dizinine gidin
cd C:\Users\dicit\Desktop\mcp\hackhaton

# Virtual environment oluşturun
python -m venv venv

# Virtual environment'ı aktif edin
venv\Scripts\activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Paketi development modunda yükleyin
pip install -e .
```

### 2. MCP Konfigürasyonu

Claude Desktop'ın MCP konfigürasyon dosyasını açın:
- Dosya konumu: `%APPDATA%\Claude\claude_desktop_config.json`
- Veya: `C:\Users\dicit\AppData\Roaming\Claude\claude_desktop_config.json`

Aşağıdaki konfigürasyonu ekleyin:

```json
{
  "mcpServers": {
    "site-crawler": {
      "command": "C:\\Users\\dicit\\Desktop\\mcp\\hackhaton\\venv\\Scripts\\python.exe",
      "args": ["-m", "site_crawler.server"],
      "cwd": "C:\\Users\\dicit\\Desktop\\mcp\\hackhaton\\src",
      "env": {
        "PYTHONPATH": "C:\\Users\\dicit\\Desktop\\mcp\\hackhaton\\src"
      }
    }
  }
}
```

**NOT**: Eğer mevcut bir konfigürasyonunuz varsa, yeni server'ı mevcut `mcpServers` objesine ekleyin.

### 3. Test Etme

1. Claude Desktop'ı yeniden başlatın
2. Claude'a şu komutu verin:
   ```
   /tools
   ```
3. `site.crawlAssets` aracının listede görünüp görünmediğini kontrol edin

### 4. Örnek Kullanım

Claude'da şu örnekleri deneyebilirsiniz:

```
Lütfen https://example.com sitesindeki tüm görselleri çıkar
```

Veya daha spesifik:

```
site.crawlAssets aracını kullanarak https://example.com sitesinden hem görselleri hem de SEO metadata'sını 2 derinliğe kadar çıkar
```

## Sorun Giderme

### MCP server görünmüyorsa:

1. Python path'inin doğru olduğundan emin olun:
   ```bash
   where python
   ```

2. Virtual environment'ın aktif olduğundan emin olun

3. Log dosyalarını kontrol edin:
   - Claude Desktop logları: `%APPDATA%\Claude\logs`

### Import hataları alıyorsanız:

1. PYTHONPATH'in doğru ayarlandığından emin olun
2. Paketi yeniden yükleyin:
   ```bash
   pip uninstall site-crawler-mcp
   pip install -e .
   ```

## Geliştirme Modu

Kod değişikliklerini test etmek için:

1. Virtual environment'ı aktif edin
2. Kodda değişiklik yapın
3. Claude Desktop'ı yeniden başlatın
4. Değişiklikleri test edin

## Testleri Çalıştırma

```bash
# Virtual environment aktifken
pytest tests/
```