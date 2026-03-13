---
title: "LibreCelik"
description: "Упутство за подешавање и коришћење LibreCelik десктоп апликације"
---

LibreCelik је десктоп апликација за читање и штампање српских државних смарт картица на Linux-у и macOS-у.

## Инсталација

### Linux

Преузмите `.AppImage` са [странице издања](https://github.com/LibreSCRS/LibreCelik/releases), дозволите извршавање и покрените:

```bash
chmod +x LibreCelik-*.AppImage
./LibreCelik-*.AppImage
```

Инсталација није потребна. AppImage садржи све зависности укључујући Qt.

#### Подршка за PC/SC читач

`pcscd` сервис мора бити покренут за приступ картици:

```bash
# Debian/Ubuntu
sudo apt install pcscd pcsc-tools
sudo systemctl enable --now pcscd

# Fedora/RHEL
sudo dnf install pcsc-lite pcsc-tools
sudo systemctl enable --now pcscd
```

Проверите да ли је ваш читач детектован:

```bash
pcsc_scan
```

### macOS

Преузмите и отворите `.dmg` са [странице издања](https://github.com/LibreSCRS/LibreCelik/releases), превуците LibreCelik у Applications.

macOS има уграђену PC/SC подршку — додатни софтвер није потребан.

---

## Подржане картице

Убаците картицу и LibreCelik аутоматски препознаје тип картице.

| Картица | Приказани подаци |
|---------|-----------------|
| Лична карта (Gemalto / IF2020) | Лични подаци, информације о документу, сертификати дигиталног потписа, управљање PIN-ом |
| Саобраћајна дозвола | Сва поља укључујући власника, возило и датуме регистрације |
| Здравствена картица | Осигураник, послодавац, детаљи осигурања |
| ПКС картица Привредне коморе | Квалификовани сертификати потписа, управљање PIN-ом |

---

## Језик

LibreCelik подржава енглески и српски (ћирилица). Промените преко менија за језик у горњем десном углу.

---

## Компајлирање из изворног кода

Погледајте [BUILDING.md](https://github.com/LibreSCRS/LibreCelik/blob/main/BUILDING.md) у изворном репозиторијуму.

**Потребно**: CMake 3.24+, Qt 6.6+, OpenSSL 3, C++20 компајлер.
