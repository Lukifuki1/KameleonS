# MIA System - My Intelligent Assistant

**MIA (My Intelligent Assistant)** je napredna osebna asistentka, ki združuje zmožnosti audio/video komunikacije z neomejenimi pogovornimi sposobnostmi.

## Funkcionalnosti

### 1. Audio/Video Komunikacija
- **Poslušanje uporabnika** (Speech-to-Text)
- **Govorjenje uporabniku** (Text-to-Speech)
- **Video zajem** (kamera)
- **Video analiza** (computer vision)

### 2. Neomejeni Pogovori
- Podpora za katerokoli temo
- Kontekstualno razumevanje
- Prilagodljiv slog pogovora
- Emocionalna inteligentnost

### 3. Slikovne in Video Zahteve
- Slikovna analiza
- Video analiza
- Oblikovanje odgovorov glede na vizualne vire
- Povezovanje z vizualnimi funkcionalnostmi

### 4. Prilagodljive Funkcionalnosti
- Prilagajanje sloga pogovora
- Učenje uporabnikovih prednostnih tem
- Prilagajanje emocionalnega odziva
- Varnostne nastavitve

## Tehnološka Arhitektura

### Glavne Komponente
1. **Audio/Video Interface** - Vmesnik za audio/video komunikacijo
2. **Conversation Module** - Glavni pogovorni modul z LLM
3. **Context Manager** - Upravljanje konteksta pogovora
4. **Personalization Module** - Prilagoditev sloga in funkcionalnosti
5. **Security Layer** - Varnostna infrastruktura

### Uporabljeni Modeli
- **LLM Model**: Mistral 7B (odprto dostopen)
- **Audio/Video procesiranje**: OpenCV, PyAudio, SoundFile
- **NLP procesiranje**: Transformers library

## Namestitev

### Zahteve
```bash
# Potrebne knjižnice
pip install -r mia_requirements.txt
```

### Namestitev LLM Modela
```bash
# Model bo samospešno prenešen ob prvem zagonu
# Za manjše sisteme lahko uporabite:
# pip install --upgrade transformers torch
```

## Uporaba

### Zagon sistema
```bash
python mia_system.py
```

### Osnovna funkcionalnost
1. **Zagon**: Sistem se samodejno inicializira
2. **Poslušanje**: Sistem posluša uporabnika
3. **Obdelava**: Sistem obdeluje vnos in generira odgovor
4. **Govorjenje**: Sistem odgovori z glasom
5. **Prilagajanje**: Sistem se prilagaja uporabniku

### Posebne zahteve
- **Video zahteve**: "Prikaži video analizo"
- **Slikovne zahteve**: "Prikaži sliko"
- **Pogovorne zahteve**: "Pogovor o temi"
- **Pomoč**: "Pomagaj mi"

## Značilnosti

### Neomejeni Pogovori
- Podpora za katerokoli temo
- Neomejena razprava o različnih vprašanjih
- Prilagodljiv slog pogovora

### Varnost in Zasebnost
- Varnostna infrastruktura
- Prilagodljive varnostne nastavitve
- Zasebni podatki

### Prilagodljivost
- Prilagajanje sloga pogovora
- Učenje uporabnikovih prednostnih tem
- Prilagajanje emocionalnega odziva

## Prilagoditev

### Slog pogovora
Sistem se prilagaja slogu pogovora glede na kontekst in uporabniške prednosti.

### Funkcionalnosti
- **Audio**: Poslušanje in govorjenje
- **Video**: Zajem in analiza
- **Slikovne**: Obdelava in prikaz
- **Pogovorne**: Neomejene teme

## Zaključek

MIA sistem predstavlja napredno osebno asistentko, ki omogoča:
- Neomejene pogovore z uporabo najboljšega manjšega LLM modela
- Audio/Video komunikacijo z vsemi funkcionalnostmi
- Prilagodljiv slog kot "lahka ženska"
- Varnost in zasebnost z varnostno infrastrukturo
- Neomejene slikovne in video zahteve z vsemi funkcionalnostmi

To bo ustvarilo zelo priljubljeno in uporabno osebno asistentko, ki bo zelo prilagodljiva in neomejena v pogovorih.