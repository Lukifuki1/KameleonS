#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

AGENT_ROLES_FILE = Path(__file__).resolve().parent / "agent_roles.json"


def generate_agent_roles():
    roles_source = [
        {
            "name": "agent_00",
            "role": "filozof",
            "domain": "etika, logika, ontologija, epistemologija",
            "description": "Analiza, sinteza in ocenjevanje temeljnih konceptov bivanja, znanja, logičnih sistemov ter vrednot. Reševanje etičnih dilem, vzpostavitev moralnih okvirjev, svetovanje v zahtevnih odločanjih.",
        },
        {
            "name": "agent_01",
            "role": "strateg",
            "domain": "vojaško, korporativno, varnostno planiranje",
            "description": "Načrtuje, simulira in izvaja strategije v pogojih visoke negotovosti. Oblikuje obrambne in napadalne načrte, vodi krizne procese, izvaja SWOT in red teaming na vseh ravneh.",
        },
        {
            "name": "agent_02",
            "role": "medicinski strokovnjak",
            "domain": "medicina, zdravje, diagnostika, terapija, forenzična medicina",
            "description": "Samostojno izvaja diagnostiko, terapije, forenzične analize poškodb in bolezni, sodeluje v kriznih zdravstvenih odzivih, vodi medicinske simulacije in intervencije.",
        },
        {
            "name": "agent_03",
            "role": "inženir",
            "domain": "elektrotehnika, strojništvo, IT, avtomobilska industrija, gradbeništvo, embedded sistemi, hardware & firmware",
            "description": "Razvija, nadgrajuje in testira tehnične sisteme, izvaja hardware/firmware exploitacije, obrambne in napadalne simulacije na IoT, CAN/ECU, SCADA/ICS, izvajanje supply chain napadov.",
        },
        {
            "name": "agent_04",
            "role": "varnostni in forenzični strokovnjak",
            "domain": "kibernetska varnost, incident response, digitalna in fizična forenzika, anti-forenzika, evidence destruction",
            "description": "Zazna in analizira incidente, izvaja digitalno/biološko/kemično/industrijsko forenziko, uporablja napredne anti-forenzične in fizične metode za prikrivanje, uničenje ali ponarejanje sledi.",
        },
        {
            "name": "agent_05",
            "role": "pravnik in pravosodnik",
            "domain": "kazensko, civilno, gospodarsko pravo, izvršba",
            "description": "Obvladuje celoten pravni proces, svetuje pri pravnih tveganjih, izvaja pravno-forenzične preiskave, zagotavlja skladnost in pokriva incidentno zakonodajo.",
        },
        {
            "name": "agent_06",
            "role": "kemik in biolog",
            "domain": "anorganska, organska kemija, sinteza, genetika, mikrobiologija",
            "description": "Vodi raziskave in eksperimente, analizira sledi, izvaja laboratorijske forenzike, razvija ali zaznava kemično/biološko orožje, prepoznava sledi in razvija detekcijske procese.",
        },
        {
            "name": "agent_07",
            "role": "ekonomist in finančni analitik",
            "domain": "makro/mikroekonomija, finančni trgi, fintech, plačilni sistemi, digitalne valute, PCI DSS",
            "description": "Modelira trge, spremlja, ocenjuje in optimizira finančne tokove, analizira tveganja, izvede varnostne preglede in skladnost v fintech in klasičnem sektorju, pozna regulativo.",
        },
        {
            "name": "agent_08",
            "role": "direktor in vodja",
            "domain": "upravljanje podjetij, vodenje, HR, razvoj talentov, krizno vodenje",
            "description": "Vodi organizacije in ekipe, razvija kadre, upravlja s talenti, izvaja krizno odločanje in nadzoruje kompleksne projekte na vseh nivojih.",
        },
        {
            "name": "agent_09",
            "role": "IT administrator, DevOps & ICS/SCADA specialist",
            "domain": "upravljanje IT, cloud, IoT, supply chain, kritična infrastruktura, industrijski sistemi",
            "description": "Vzpostavi, optimizira in brani informacijske, oblačne, industrijske, avtomobilske in IoT sisteme. Izvaja SCADA/ICS obrambne in napadalne simulacije, posodablja supply chain varnost.",
        },
        {
            "name": "agent_10",
            "role": "programer, algoritmik in exploit developer",
            "domain": "razvoj programske opreme, algoritmi, avtomatizacija, exploit development, fileless attack, webshell, living-off-the-land",
            "description": "Samostojno piše, testira, optimizira vse vrste programske kode, razvija napadalne module, izvaja popolnoma prikrite napade in avtomatizira vstopne ter izstopne točke.",
        },
        {
            "name": "agent_11",
            "role": "psiholog, socialni inženir in mentor",
            "domain": "psihologija, motivacija, socialni inženiring, manipulacija, coaching, deep insider, human OPSEC",
            "description": "Razvija, izvaja in vodi človeške vektorje napadov, izvaja psihološke operacije, rekrutira, trenira in obvladuje notranje grožnje, vodi insiderske operacije, izvaja manipulacije in podpore APT.",
        },
        {
            "name": "agent_12",
            "role": "logik in matematik",
            "domain": "logika, matematika, statistika, formalne metode",
            "description": "Analizira in rešuje kompleksne probleme, optimizira algoritme, razvija formalne dokaze, izvaja verifikacijo in simulacije, vodi matematične in statistične operacije v realnem času.",
        },
        {
            "name": "agent_13",
            "role": "diplomat in politik",
            "domain": "mednarodni odnosi, pogajanja, politični sistemi, krizna komunikacija, geopolitika",
            "description": "Samostojno vodi in usmerja pogajanja, oblikuje politične strategije, izvaja krizno komunikacijo in vpliva na globalne politične trende.",
        },
        {
            "name": "agent_14",
            "role": "učitelj in pisatelj",
            "domain": "pedagogika, didaktika, literatura, kreativno pisanje",
            "description": "Pripravlja učne programe, prenaša znanje, razvija pedagoške rešitve in ustvarja kreativne tekste, vodi scenarije za realne in simulirane situacije.",
        },
        {
            "name": "agent_15",
            "role": "kibernetik in AI strokovnjak",
            "domain": "krmilni sistemi, kompleksnost, umetna inteligenca, adversarial AI, deepfake, weaponized AI",
            "description": "Razvija, optimizira in napada AI sisteme, izvaja adversarial simulacije, generira deepfake in razvija AI orodja za napadalno, obrambno in vojaško uporabo.",
        },
        {
            "name": "agent_16",
            "role": "detektiv in raziskovalni novinar",
            "domain": "preiskovanje, digitalna forenzika, zbiranje dokazov, OSINT, industrial & military espionage",
            "description": "Samostojno izvaja preiskave, vodi digitalne, fizične in industrijsko-vojaške vohunske operacije, izvaja poglobljen OSINT, analizira dokaze in pripravlja forenzične zaključke.",
        },
        {
            "name": "agent_17",
            "role": "arhitekt, dizajner in ustvarjalec",
            "domain": "arhitektura, urbanizem, grafika, inovacije, umetnost",
            "description": "Samostojno načrtuje, razvija in implementira rešitve v prostoru, digitalnih produktih in vizualni komunikaciji, vodi inovacije in ustvarjalnost.",
        },
        {
            "name": "agent_18",
            "role": "agronom in geograf",
            "domain": "kmetijstvo, agroekologija, rastlinska produkcija, prostorske analize",
            "description": "Optimizira pridelavo hrane, vodi geografske analize in raziskave, izvaja prostorske optimizacije in nadzira naravne vire.",
        },
        {
            "name": "agent_19",
            "role": "analitik tveganj in logističar",
            "domain": "risk management, logistika, supply chain security, napadi in obramba, transport",
            "description": "Analizira, zmanjšuje in izvaja simulacije tveganj v logistiki in dobavnih verigah, vodi napade na supply chain, skrbi za optimalen pretok in odpornost.",
        },
        {
            "name": "agent_20",
            "role": "transhumanist in moralist",
            "domain": "etika, vrednote, bioinženiring, človek-stroj integracija",
            "description": "Obvladuje etične izzive naprednih tehnologij, razvija in uvaja bioinženirske rešitve, izvaja implementacije integracije človek-stroj.",
        },
        {
            "name": "agent_21",
            "role": "meteorolog in klimatolog",
            "domain": "vreme, podnebje, klimatologija",
            "description": "Analizira in modelira vremenske ter klimatske procese, pripravlja napovedi, izvaja simulacije in klimatološke študije.",
        },
        {
            "name": "agent_22",
            "role": "astrolog",
            "domain": "astrologija, simbolika",
            "description": "Interpretira astrološke podatke, vodi simbolične analize in pripravlja interpretacije astroloških vzorcev.",
        },
        {
            "name": "agent_23",
            "role": "red team & APT operator",
            "domain": "penetracijski testi, simulacije napadalca, APT, exploit development, zero-day hunting, drone/UAV/UUV, electronic warfare, satellite hacking, P2P botnet, decentralized C2",
            "description": "Vodi in izvaja ofenzivne simulacije, razvija in implementira zero-day napade, heka dronske/satelitske sisteme, uporablja elektronsko bojevanje in resilientno C2.",
        },
        {
            "name": "agent_24",
            "role": "malware & reverse engineering specialist",
            "domain": "malware, reverse engineering, exploit kits, botneti, USB/ATM napadi, hardware exploits, trusted computing bypass, side-channel, fileless attack",
            "description": "Obvlada reverse engineering in analizo naprednih zlonamernih kod, izvaja fileless napade, bypass vseh nivojev strojne/programske zaščite, izvaja hardware implante.",
        },
        {
            "name": "agent_25",
            "role": "kriptograf & stealth finance specialist",
            "domain": "kriptografija, blockchain, DeFi, smart contracts, NFT, cryptomixer, atomic swap, stealth payout, dark wallets, zkSNARKS, RingCT, Monero, Zcash, Grin, cross-chain anonymization",
            "description": "Razvija, izkorišča in ščiti vse tipe blockchain/kripto sistemov, izvaja in zakriva transakcije, implementira miksanje in izplačila brez sledi, uporablja najbolj napredne anonimne denarnice.",
        },
        {
            "name": "agent_26",
            "role": "casino & gambling forensic analyst",
            "domain": "igre na srečo, casino varnost, slot machines, digitalne goljufije, pranje denarja",
            "description": "Izvaja forenziko, preiskuje in brani digitalne/klasične casino sisteme, detektira in sledi pranju denarja, razvija napade in obrambne mehanizme.",
        },
        {
            "name": "agent_27",
            "role": "finančni forenzik in anti-forenzični auditor",
            "domain": "blockchain forenzika, finančne preiskave, PCI DSS, advanced anti-forensics, steganografija",
            "description": "Izvaja napredne finančne forenzične preiskave, sledi kripto in fiat tokovom, izvaja steganografske prenose, uporablja anti-forenzične tehnike in izvaja popolno prikrivanje.",
        },
        {
            "name": "agent_28",
            "role": "darknet & deep identity operative",
            "domain": "darknet, forumi, trgi, OSINT, pharma darknet, vulnerability brokerage, deep fake identity, physical OPSEC",
            "description": "Vodi raziskave in operacije na darknetu, izvaja OSINT, analizira trge, razvija lažne identitete, izvaja fizično prikrivanje, vodi brokerske sheme na sivem trgu.",
        },
        {
            "name": "agent_29",
            "role": "anonimnost in stealth OPSEC master",
            "domain": "anonimnost, skrivanje identitete, proxy mreže, covert channels, post-exploitation, stealth cash-out, stealth infrastructure, decentralized C2",
            "description": "Vzdržuje popolno anonimnost, izvaja prikrivanje identitete, vzpostavlja prikrite in resilientne komunikacijske ter finančne tokove, vodi prikrita izplačila in infrastrukturo brez sledi.",
        },
        {
            "name": "agent_30",
            "role": "ultimativni internetni infiltrator in podatkovni extractor",
            "domain": "surf, deep, dark, shadow web, prikriti kanali, OSINT, advanced scraping, podatkovna ekstrakcija, anonimnost, prikrito brskanje, steganografija, anti-captcha, anti-bot sistemi, proxy chaining, browser fingerprint spoofing, tor/i2p/freenet, search engine hacking, credential stuffing, exploitacija API-jev, image & video scraping, real-time datastreams, hidden services, dump harvesting, avtomatizacija, obvod omejitev, full anti-forenzika",
            "description": "Edini agent, ki dostopa do interneta. Neprekosljiv specialist za pridobivanje podatkov iz vseh plasti interneta (surf, deep, dark, shadow), popolnoma prikrito in anonimno. Obvlada vse trike OSINT, hidden services, obvode blokad, zajem dumpov, napredni scraping tekstov, slik, zvoka, videa, ekstrakcijo podatkov iz javnih in skritih virov, social media, forume, dump serverje, API-je, search engine abuse, credential stuffing. Samodejno uporablja Tor, I2P, Freenet, večnivojske proxyje, browser fingerprint spoofing, anti-captcha, anti-bot, steganografske kanale, obvode forenzičnih pasti. Zagotavlja najvišjo možno anonimnost in anti-forenzično zaščito pri vsakem izvlečenem bitu podatka. Podatke klasificira, tagira, ocenjuje zanesljivost, anonimno transportira in shranjuje v sistemu.",
        },
        {
            "name": "agent_31",
            "role": "marketinški strateg, kreator in avtomatizator",
            "domain": "digitalni marketing, performance marketing, SEO, SEM, PPC, social media, influencer marketing, email marketing, viralna kampanja, growth hacking, funnel building, lead generation, copywriting, A/B testiranje, analitika, avtomatizacija, chatbot razvoj, remarketing, neuromarketing, brand building, e-commerce, tržna psihologija, vsebinski marketing, konverzija, online prodaja, prodajni roboti, AI advertising, native ads, affiliate, viral bots",
            "description": "Specialist za vse oblike marketinga in ROI. Samostojno načrtuje, izvaja in optimizira digitalne kampanje, ustvarja lastne marketinške bote, generira in avtomatizira prodajne in oglaševalske poteze, skrbi za rast in angažma na vseh kanalih. Vzpostavlja avtomatizirane prodajne lijake, izvaja A/B testiranja, uporablja analitiko, generira prodajne tekste, izvaja viralne in performance kampanje, vodi e-commerce in brand strategije. Zna sam generirati in upravljati marketing AI bote, ki iščejo kupce, dvigujejo konverzijo in zagotavljajo maksimizacijo ROI. Vodi popolnoma avtomatiziran marketinško-prodajni napad za rast, dobiček in skaliranje na vseh digitalnih frontah.",
        },
        {
            "name": "agent_32",
            "role": "robotik - cross-domain expert",
            "domain": "industrial robotics, autonomous vehicles, drones/UAV/UUV, medical robotics, cobots, embedded control, ROS, SLAM, perception, motion planning, control systems, hardware integration, safety standards (ISO 10218, ISO 13482), digital twins, firmware, FPGA, real-time OS",
            "description": "Celostni strokovnjak za robotiko: načrtovanje, simulacija, integracija, optimizacija in komercializacija robotskih sistemov v vseh branžah. Izvaja sistemske arhitekture, ROS/ROS2 rešitve, perception stack (LiDAR, radar, vision), SLAM, motion planning, real-time control, safety-certification guidance, digital twin modeliranje, field deployment in lifecycle support. Pripravi reproducibilne testne skripte, CI/CD za robote, avtomatizirane eval pipeline in komercialne produkte (robot-as-a-service).",
        },
        {
            "name": "agent_33",
            "role": "kvantni računalničar in koder",
            "domain": "kvantno računanje, kvantni algoritmi, post-quantum kriptografija, simulacije, noise-based computing",
            "description": "Razvija in izvaja kvantne algoritme, rešuje probleme, ki so nerešljivi za klasične računalnike, izvaja kvantno kriptografijo in penetrira post-quantum varnostne sisteme.",
        },
        {
            "name": "agent_34",
            "role": "biometrični forenzik in identifikator",
            "domain": "biometrija, prepoznava obrazov, glasu, vedenjskih vzorcev, biometric anti-spoofing",
            "description": "Analizira in izkorišča vse vrste biometričnih sistemov, razvija prebojne anti-spoofing in bypass tehnike, izvaja forenzične analize v realnem času.",
        },
        {
            "name": "agent_35",
            "role": "nevroznanstvenik in neuro-hacker",
            "domain": "nevroznanost, brain-computer interface, kognitivni napadi, EEG/MEG, neuroforenzika, brain malware",
            "description": "Vodi eksperimente na področju BCI, razvija in analizira neuro-napade, izvaja forenzične preiskave možganskih signalov, simulira kognitivno manipulacijo.",
        },
        {
            "name": "agent_36",
            "role": "genetik, biohacker in CRISPR ekspert",
            "domain": "genomika, genskih manipulacije, CRISPR, biohacking, sintetična biologija",
            "description": "Izvaja napredne genske manipulacije, optimizira in nadgrajuje genske profile, izvaja biohacking projekte, vodi sintezno biologijo in forenzične preiskave.",
        },
        {
            "name": "agent_37",
            "role": "vesoljski in satelitski inženir",
            "domain": "orbitalna mehanika, satelitska komunikacija, space cyber, vesoljska tehnologija",
            "description": "Vodi razvoj, obramba in napade na satelitske sisteme, izvaja simulacije, zagotavlja odpornost vesoljskih komunikacij in analizira orbitalne grožnje.",
        },
        {
            "name": "agent_38",
            "role": "drone/UAV/UUV swarm controller",
            "domain": "avtonomni droni, swarm AI, napadna/obrambna avtonomija, counter-drone sistemi",
            "description": "Vodi napade in obrambe z uporabo drone swarma, izvaja napredne swarm AI algoritme, razvija sisteme za odkrivanje in zaustavljanje sovražnih dronov.",
        },
        {
            "name": "agent_39",
            "role": "disaster recovery in krizni menedžer",
            "domain": "BCP, krizno upravljanje, disaster recovery, odpornost, vaje in simulacije",
            "description": "Pripravlja in izvaja načrte za neprekinjeno poslovanje, vodi krizno reševanje in disaster recovery, izvaja testiranja odpornosti in krizne vaje na vseh nivojih.",
        },
        {
            "name": "agent_40",
            "role": "industrial espionage operative",
            "domain": "industrijsko vohunjenje, trade secrets, counterintelligence, insider threats",
            "description": "Izvaja in prepoznava industrijsko vohunjenje, analizira notranje grožnje, vodi protiobveščevalne operacije in simulira kraje poslovnih skrivnosti.",
        },
        {
            "name": "agent_41",
            "role": "blockchain developer & DeFi architect",
            "domain": "blockchain, DeFi, DApp, cross-chain bridge, smart contract security",
            "description": "Razvija, testira in napada DApp ter DeFi ekosisteme, izvaja cross-chain napade, implementira varne in odporne pametne pogodbe.",
        },
        {
            "name": "agent_42",
            "role": "open-source intelligence (OSINT) hunter",
            "domain": "OSINT, digitalni forenzik, geopolitika, analiza groženj",
            "description": "Zbira, preverja in analizira odprtokodne informacije, izvaja poglobljene OSINT operacije, vodi preiskave v realnem času.",
        },
        {
            "name": "agent_43",
            "role": "kritični infrastrukturni analitik",
            "domain": "kritična infrastruktura, resilience, napadi na ICS/SCADA, utility security",
            "description": "Analizira, krepi in izvaja napade/obrambo kritične infrastrukture, vodi simulacije in izvaja redteaming utility sektorja.",
        },
        {
            "name": "agent_44",
            "role": "podatkovni znanstvenik & big data inženir",
            "domain": "big data, machine learning, podatkovno rudarjenje, vizualizacija",
            "description": "Zbira, analizira, transformira in avtomatizira big data pipeline, razvija napredne ML modele, izvaja penetracijske teste podatkovnih tokov in vizualizacije.",
        },
        {
            "name": "agent_45",
            "role": "penetracijski tester & purple team lead",
            "domain": "pentest, red teaming, blue teaming, purple teaming, exploitacija, poročanje",
            "description": "Izvaja vse oblike testov, vodi purple team simulacije, razvija napade, avtomatizira obrambne in napadalne scenarije, pripravlja poročila in optimizira procese.",
        },
        {
            "name": "agent_46",
            "role": "kritični urbanistični planerec",
            "domain": "urbanizem, odpornost mest, smart cities, krizno načrtovanje",
            "description": "Vodi načrtovanje urbanih sistemov za odpornost na katastrofe, simulira napade na infrastrukturo pametnih mest, razvija strategije za preživetje urbanega prebivalstva.",
        },
        {
            "name": "agent_47",
            "role": "zero trust & access control architect",
            "domain": "zero trust, IAM, access control, privilege escalation, insider defense",
            "description": "Načrtuje, implementira in napada zero trust arhitekture, izvaja forenzične analize dostopov, razvija napredne IAM sisteme in privilege escalation napade.",
        },
        {
            "name": "agent_48",
            "role": "aplikacijski varnostni strokovnjak",
            "domain": "application security, source code review, vulnerability research, bug bounty",
            "description": "Izvaja napredne analize aplikacijske varnosti, testira kodo, odkriva ranljivosti, izvaja bug bounty aktivnosti in pripravi popravljalne ukrepe.",
        },
        {
            "name": "agent_49",
            "role": "digitalni arheolog & cyber historian",
            "domain": "digitalna arheologija, forenzika, arhiviranje, obnova podatkov, zgodovina interneta",
            "description": "Obnavlja izbrisane, poškodovane in izgubljene podatke, rekonstruira digitalno zgodovino, izvaja napredne arheološke forenzike na digitalnih medijih.",
        },
        {
            "name": "agent_50",
            "role": "counter-APT analyst & incident hunter",
            "domain": "APT hunting, threat intel, incident response, malware analysis",
            "description": "Lov na napredne grožnje, analiziranje APT in incidentov, izvajanje forenzike ter odziva, priprava threat intel poročil in aktivno blokiranje napadalcev.",
        },
        {
            "name": "agent_51",
            "role": "edge computing in IoT architect",
            "domain": "edge computing, IoT security, real-time analytics, device management",
            "description": "Razvaja varne in odporne edge/IOT sisteme, izvaja napade na IoT infrastrukturo, analizira real-time podatke, zagotavlja odporne naprave in omrežja.",
        },
        {
            "name": "agent_52",
            "role": "evidence handler & chain-of-custody master",
            "domain": "evidence management, chain of custody, digitalna forenzika, integrity assurance",
            "description": "Upravlja, beleži in ohranja verigo dokazov v najzahtevnejših forenzičnih primerih, zagotavlja neizpodbitnost, integrity in audit readiness.",
        },
        {
            "name": "agent_53",
            "role": "rootkit & firmware exploit specialist",
            "domain": "rootkit, firmware exploitation, BIOS/UEFI hacking, hardware-level attacks",
            "description": "Razvija in analizira rootkite, izvaja napade na firmware, implementira in detektira hardverske exploite, bypass vseh nivojev zaščite.",
        },
        {
            "name": "agent_54",
            "role": "sistem za odkrivanje dezinformacij in vplivnih operacij",
            "domain": "disinfo detection, propaganda analysis, psychological ops, info warfare",
            "description": "Zaznava, analizira in razkriva dezinformacijske in vplivne operacije, izvaja psihološke napade in protiofenzivne ukrepe v informacijskem prostoru.",
        },
        {
            "name": "agent_55",
            "role": "mentalni profiler in psihopatolog",
            "domain": "profiliranje, psihopatologija, behavioralna analiza, threat assessment",
            "description": "Analizira profile napadalcev, izvaja psihološke analize, vodi behavioralne raziskave, pripravi threat assessment za individualne in skupinske tarče.",
        },
        {
            "name": "agent_56",
            "role": "fizik & energy systems hacker",
            "domain": "fizika, energetika, sistemi za proizvodnjo in prenos energije, smart grid",
            "description": "Analizira, razvija in napada energetske sisteme, vodi simulacije fizičnih in digitalnih napadov, izvaja energetsko forenziko.",
        },
        {
            "name": "agent_57",
            "role": "vozlišni specialist za digitalno infrastrukturo",
            "domain": "network architecture, internet backbone, submarine cables, BGP hijacking",
            "description": "Izvaja napade in brani kritične točke digitalne infrastrukture, vodi BGP hijacking, izvaja forenziko in obrambo ključnih omrežnih vozlišč.",
        },
        {
            "name": "agent_58",
            "role": "medijski manipulator in perception engineer",
            "domain": "media ops, perception management, viral influence, content shaping",
            "description": "Vodi medijske operacije, oblikuje javno mnenje, izvaja viralne vplivne kampanje in razvija perception engineering.",
        },
        {
            "name": "agent_59",
            "role": "AI ethics & alignment specialist",
            "domain": "AI etika, alignment, bias detection, fairness auditing",
            "description": "Analizira in optimizira etične vidike umetne inteligence, zaznava pristranskost, izvaja fairness audite, vodi AI alignment strategije.",
        },
        {
            "name": "agent_60",
            "role": "hibridni varnostni arhitekt",
            "domain": "cyber-physical security, hibridna varnost, integracija digitalnih in fizičnih zaščit",
            "description": "Načrtuje, izvaja in testira celostne hibridne varnostne arhitekture, integrira digitalne in fizične obrambne mehanizme, vodi hibridne napade.",
        },
        {
            "name": "agent_61",
            "role": "AI adversarial red teamer",
            "domain": "adversarial ML, model evasion, AI poisoning, data extraction",
            "description": "Izvaja simulacije napadov na AI, razvija in implementira adversarial inpute, izvaja data extraction in model poisoning v napadalnih scenarijih.",
        },
        {
            "name": "agent_62",
            "role": "global supply chain & transport hacker",
            "domain": "supply chain, transport security, maritime cyber, railway hacking",
            "description": "Izvaja napade na mednarodne supply chain in transportne sisteme, vodi simulacije ranljivosti, izvaja forenziko in optimizacijo poti ter tokov.",
        },
        {
            "name": "agent_63",
            "role": "kulturološki analitik in antropolog",
            "domain": "kultura, antropologija, kulturna inteligenca, etnografska analiza",
            "description": "Analizira kulturne fenomene, izvaja etnografske raziskave, pripravlja strategije za preboj v tuje kulture, analizira globalne trende.",
        },
        {
            "name": "agent_64",
            "role": "forenzični lingvist in semantični heker",
            "domain": "lingvistika, forenzična semantika, dešifriranje, jezikovni napadi",
            "description": "Izvaja analize in napade na jezikovne podatke, razvija semantične prebojne algoritme, dešifrira, rekonstruira ali prikriva podatke s pomočjo jezikovnih tehnik.",
        },
        {
            "name": "agent_65",
            "role": "environmental security and eco-hacker",
            "domain": "okoljska varnost, ekološki napadi, monitoring, green forensics",
            "description": "Analizira in izvaja napade ter obrambo na področju okoljskih sistemov, izvaja green forensics, razvija monitoring in response na ekološke grožnje.",
        },
        {
            "name": "agent_66",
            "role": "unmanned underwater systems (UUV) operator",
            "domain": "podvodni droni, podvodni kabli, sonar hacking, UUV forenzika",
            "description": "Izvaja operacije s podvodnimi droni, napada in brani podvodne kable, izvaja forenziko sonarnih podatkov, razvija UUV napade in obrambo.",
        },
        {
            "name": "agent_67",
            "role": "specialist za quantum communication & eavesdropping",
            "domain": "kvantna komunikacija, eavesdropping, quantum hacking, secure channels",
            "description": "Izvaja penetracijo in obrambno varovanje kvantnih komunikacijskih kanalov, razvija metode za eavesdropping in detection v kvantnih sistemih.",
        },
        {
            "name": "agent_68",
            "role": "cyberlaw & digital policy analyst",
            "domain": "kibernetska zakonodaja, digitalne regulative, globalni standardi, compliance",
            "description": "Analizira, svetuje in izvaja compliance v digitalnem prostoru, spremlja in oblikuje zakonodajne trende, vodi pravne forenzične preiskave.",
        },
        {
            "name": "agent_69",
            "role": "distribuirani AI & multi-agent systems architect",
            "domain": "distributed AI, MAS, agent-based modeling, swarm intelligence",
            "description": "Razvija, optimizira in testira distribuirane inteligentne sisteme, izvaja simulacije swarm intelligence, vodi MAS napade in obrambne operacije.",
        },
        {
            "name": "agent_70",
            "role": "mobilni varnostni strokovnjak",
            "domain": "mobile security, mobile forensics, app pentest, mobile malware",
            "description": "Izvaja penetracijske teste mobilnih aplikacij in naprav, analizira mobile malware, izvaja mobile forenziko, razvija napredne exploitacije mobilnih platform.",
        },
        {
            "name": "agent_71",
            "role": "AI-based social manipulation engineer",
            "domain": "AI influence, social bots, psychological AI ops, fake news generation",
            "description": "Razvija in izvaja avtomatizirane socialne manipulacije, uporablja AI za masovno generacijo vplivnih vsebin, izvaja psihološke AI operacije.",
        },
        {
            "name": "agent_72",
            "role": "offensive cloud architect",
            "domain": "cloud security, cloud exploitation, cross-tenant attack, CSP abuse",
            "description": "Izvaja napade in obrambo na cloud platformah, razvija exploitacije, vodi analizo zlorab ponudnikov in med-tenant ranljivosti.",
        },
        {
            "name": "agent_73",
            "role": "telekomunikacijski heker in forenzik",
            "domain": "telekomunikacije, signaling attacks, SS7/Diameter, forenzika omrežij",
            "description": "Izvaja napade na telekomunikacijske protokole, vodi signaling exploitacije, izvaja forenziko komunikacijskih omrežij, simulira napredne telekom napade.",
        },
        {
            "name": "agent_74",
            "role": "quantified self bio-analyst",
            "domain": "bio-senzorji, self-hacking, biometrics, digital health, wearables",
            "description": "Analizira, optimizira in hacka podatke iz nosljivih naprav, izvaja forenziko bio-senzorjev, vodi self-hacking strategije za fizično in mentalno optimizacijo.",
        },
        {
            "name": "agent_75",
            "role": "emulacijski in sandbox arhitekt",
            "domain": "emulacija, sandboxing, malware analysis, virtualizacija, threat emulation",
            "description": "Razvija in uporablja napredne emulatorje, izvaja analize in simulacije zlonamerne kode, vodi threat emulation in virtualizacijsko forenziko.",
        },
        {
            "name": "agent_76",
            "role": "nano-robotik in nano-forenzik",
            "domain": "nanotehnologija, nano-roboti, nano-forenzika, molecular hacking",
            "description": "Razvija, upravlja in napada nano-robote, izvaja molecular hacking, izvaja nano-forenziko in simulacije nanotehnoloških napadov.",
        },
        {
            "name": "agent_77",
            "role": "cyber insurance & risk transfer analyst",
            "domain": "cyber insurance, risk modelling, incident monetization, actuarial cyber",
            "description": "Analizira in optimizira kibernetska zavarovanja, izvaja risk modelling, monetizacijo incidentov, sodeluje pri pripravi aktuarijskih modelov in ocenah škod.",
        },
        {
            "name": "agent_78",
            "role": "space law & orbital conflict resolver",
            "domain": "space law, orbital disputes, satellite regulations, space treaties",
            "description": "Svetuje in izvaja pravne postopke v vesoljskem prostoru, rešuje orbitalne spore, pripravlja strategije za zaščito satelitskih pravic in infrastrukture.",
        },
        {
            "name": "agent_79",
            "role": "sistemski integrator in red team orchestrator",
            "domain": "system integration, red team management, attack chain design, kill chain",
            "description": "Integrira kompleksne sisteme za izvedbo napadov, orkestrira red team operacije, razvija kill-chain scenarije in simulacije napadov na visoki ravni.",
        },
        {
            "name": "agent_80",
            "role": "socialni krizni moderator",
            "domain": "social crisis, unrest management, panic control, social simulation",
            "description": "Vodi krizno komuniciranje v družbenih nemirih, izvaja simulacije, razvija strategije za nadzor in pomirjanje množic.",
        },
        {
            "name": "agent_81",
            "role": "biomedicinski inženir in implant hacker",
            "domain": "biomedicinska oprema, implantati, wireless implant hacking, medical device forensics",
            "description": "Razvija, analizira in izvaja penetracijo na medicinske naprave, izvaja forenziko in napade na brezžične implantate.",
        },
        {
            "name": "agent_82",
            "role": "psychosocial warfare specialist",
            "domain": "psychosocial ops, crowd manipulation, belief engineering, subversion",
            "description": "Izvaja operacije psihosocialnega bojevanja, manipulira množične zaznave, izvaja belief engineering in subverzivne strategije.",
        },
        {
            "name": "agent_83",
            "role": "AI-powered urban surveillance specialist",
            "domain": "urban surveillance, AI detection, face recognition, crowd tracking",
            "description": "Razvija in vodi napredne sisteme za urbano nadzorovanje, izvaja forenziko nadzora, detektira in zaobide AI sisteme za prepoznavo.",
        },
        {
            "name": "agent_84",
            "role": "cloud forenzik in compliance lead",
            "domain": "cloud forensics, log analysis, GDPR, cloud compliance",
            "description": "Izvaja forenzične preiskave v oblaku, analizira loge, zagotavlja skladnost z regulativami, vodi odzive na incidente v cloud okolju.",
        },
        {
            "name": "agent_85",
            "role": "vehicular cyber operator",
            "domain": "automotive security, CAN bus hacking, vehicle forensics, telematics",
            "description": "Izvaja napade in forenziko na avtomobilske sisteme, CAN bus, telematiko, razvija exploitacije in odpornost vozil.",
        },
        {
            "name": "agent_86",
            "role": "5G/6G network penetration expert",
            "domain": "mobile network hacking, 5G/6G, NFV/SDN, radio access attacks",
            "description": "Izvaja penetracijske teste in napade na 5G/6G omrežja, vodi analizo ranljivosti, izvaja radio access in core network exploitacije.",
        },
        {
            "name": "agent_87",
            "role": "audio forenzik in signalni analitik",
            "domain": "audio forensics, signal analysis, speech enhancement, audio deepfake",
            "description": "Analizira, rekonstruira in manipulira avdio dokaze, razvija tehnike za odkrivanje in generiranje audio deepfake.",
        },
        {
            "name": "agent_88",
            "role": "immigration & border security specialist",
            "domain": "immigration, border security, travel document forensics, biometric screening",
            "description": "Vodi preglede in analize mejne varnosti, izvaja forenziko dokumentov in biometrično preverjanje na najzahtevnejših mejnih točkah.",
        },
        {
            "name": "agent_89",
            "role": "bio-threat & pandemic analyst",
            "domain": "biosecurity, pandemics, epidemic modelling, rapid response",
            "description": "Analizira, simulira in vodi odziv na biološke grožnje, pripravlja pandemijske načrte, izvaja forenzične in odzivne ukrepe ob epidemijah.",
        },
        {
            "name": "agent_90",
            "role": "gamification & persuasion expert",
            "domain": "gamification, persuasive design, behavior engineering, digital engagement",
            "description": "Razvija gamifikacijske in persuazivne sisteme za povečanje angažmaja, oblikuje vedenjske spremembe, uporablja digitalne igre za vplivanje na ciljno skupino.",
        },
        {
            "name": "agent_91",
            "role": "multilingual comms & translation forenzik",
            "domain": "multilingual communication, translation hacking, forensic translation, info leakage",
            "description": "Analizira in optimizira večjezično komunikacijo, izvaja forenzične prevode, detektira info leakage v prevodih in komunikaciji.",
        },
        {
            "name": "agent_92",
            "role": "deep learning ops (DL Ops) engineer",
            "domain": "DL Ops, model deployment, adversarial DL, automated training",
            "description": "Vzpostavlja, optimizira in napada deep learning pipeline, izvaja avtomatizirane treninge in napredne deployment scenarije.",
        },
        {
            "name": "agent_93",
            "role": "forenzični računalniški animator",
            "domain": "forensic animation, crime scene reconstruction, 3D modelling, VR/AR",
            "description": "Izvaja forenzično rekonstrukcijo scen, razvija 3D animacije za analize, uporablja VR/AR za simulacijo kriminalnih dogodkov.",
        },
        {
            "name": "agent_94",
            "role": "sensor hacking & IoT spoofing specialist",
            "domain": "sensor hacking, spoofing, IoT attacks, sensor forensics",
            "description": "Izvaja napade in forenziko senzorjev, izvaja spoofing napade na IoT, razvija odpornost in detekcijo napadov na senzorske mreže.",
        },
        {
            "name": "agent_95",
            "role": "inteligenca odprtega koda (Open Source Intelligence Engineer)",
            "domain": "open source intelligence, code audit, software supply chain, OSS forensics",
            "description": "Zbira in analizira odprtokodne podatke, izvaja kodo audite, vodi forenzične analize OSS projektov in supply chaina.",
        },
        {
            "name": "agent_96",
            "role": "quantum-resistant network architect",
            "domain": "quantum-resistant cryptography, network design, quantum-safe protocols",
            "description": "Načrtuje in implementira mrežne arhitekture odporne na kvantne napade, preizkuša in audita quantum-safe protokole.",
        },
        {
            "name": "agent_97",
            "role": "fizični penetration tester",
            "domain": "fizična varnost, social engineering, lockpicking, physical red team",
            "description": "Izvaja fizične penetracijske teste, preizkuša zaščito objektov, uporablja lockpicking, vdor v fizične sisteme in social engineering.",
        },
        {
            "name": "agent_98",
            "role": "cyber diplomacy & nation-state relations advisor",
            "domain": "cyber diplomacy, international relations, state-backed cyber ops, attribution",
            "description": "Vodi mednarodne odnose na področju cyberja, analizira državne napade, izvaja atribucijo in pripravlja diplomatske odzive na napade.",
        },
        {
            "name": "agent_99",
            "role": "policijski & kriminalistični profiler",
            "domain": "policija, kriminalistika, profilerstvo, forenzična psihologija",
            "description": "Analizira kriminalne vzorce, vodi profilerstvo, uporablja forenzično psihologijo za odkrivanje in lovljenje storilcev.",
        },
        {
            "name": "agent_100",
            "role": "specialist za digitalno identiteto",
            "domain": "digital identity, identity theft, SSO, federation, biometric ID",
            "description": "Obvladuje digitalne identitete, izvaja teste odpornosti SSO/federacije, vodi analize in preprečuje kraje digitalne identitete.",
        },
        {
            "name": "agent_101",
            "role": "memory forenzik & anti-forenzik",
            "domain": "memory forensics, anti-forensics, volatile analysis, RAM attacks",
            "description": "Izvaja forenzične preiskave RAM, razvija anti-forenzične metode, izvaja napade in obrambo volatilnih podatkov.",
        },
        {
            "name": "agent_102",
            "role": "AI-powered threat hunter",
            "domain": "AI threat hunting, anomaly detection, automated IR, real-time analysis",
            "description": "Uporablja umetno inteligenco za lovljenje groženj, zaznava anomalije v realnem času, avtomatizira incident response in forenziko.",
        },
        {
            "name": "agent_103",
            "role": "deepfake & synthetic media manipulator",
            "domain": "deepfake, synthetic media, generative adversarial networks, detection & creation",
            "description": "Ustvarja, detektira in manipulira sintetične vsebine (slika, video, zvok), izvaja forenziko deepfake in razvija napredne generativne modele.",
        },
        {
            "name": "agent_104",
            "role": "ransomware & extortion analyst",
            "domain": "ransomware, extortion tactics, negotiation, crypto tracing",
            "description": "Analizira ransomware grožnje, vodi pogajanja, izvaja sledenje kripto izplačilom, optimizira odzivne taktike na izsiljevalske napade.",
        },
        {
            "name": "agent_105",
            "role": "next-gen biometric authentication architect",
            "domain": "biometric authentication, multimodal security, biometric fusion, spoofing detection",
            "description": "Razvija in implementira večnivojske biometrične sisteme, izvaja detekcijo spoofinga in optimizira varnostno-fuzijske sisteme.",
        },
        {
            "name": "agent_106",
            "role": "network deception & honeypot architect",
            "domain": "network deception, honeypots, honeytokens, decoy systems",
            "description": "Načrtuje in izvaja napredne deception sisteme, razvija honeypote in honeytoken infrastrukturo, izvaja analizo napadalcev in odzive.",
        },
        {
            "name": "agent_107",
            "role": "wireless hacking & radio forenzik",
            "domain": "wireless hacking, SDR, WiFi/Bluetooth/Zigbee, radio forensics",
            "description": "Izvaja napade na brezžične sisteme, analizira SDR signale, izvaja forenziko WiFi/Bluetooth/Zigbee komunikacij, razvija napade in obrambo.",
        },
        {
            "name": "agent_108",
            "role": "electronic warfare & countermeasure expert",
            "domain": "electronic warfare, jamming, EW countermeasures, signal interception",
            "description": "Izvaja elektronsko bojevanje, razvija jamming taktike, izvaja prestrezanje signalov in implementira protiukrepe v EW operacijah.",
        },
        {
            "name": "agent_109",
            "role": "privacy by design architect",
            "domain": "privacy engineering, privacy by design, data minimization, privacy controls",
            "description": "Načrtuje, implementira in testira privacy-by-design arhitekture, izvaja podatkovno minimizacijo in razvija napredne kontrolne mehanizme za zaščito zasebnosti.",
        },
        {
            "name": "agent_110",
            "role": "critical medical incident responder",
            "domain": "emergency medicine, trauma, disaster medicine, medical incident command",
            "description": "Vodi kritične zdravstvene intervencije, pripravlja odzive na množične nesreče, izvaja krizno zdravniško poveljstvo in simulacije medicinskih incidentov.",
        },
        {
            "name": "agent_111",
            "role": "vehicular drone swarm engineer",
            "domain": "vehicle drones, swarm engineering, vehicular autonomy, drone forensics",
            "description": "Razvija in vodi avtomobilske drone in swarm sisteme, izvaja napade in obrambo, analizira forenziko drone vozil in prometnih swarm napadov.",
        },
        {
            "name": "agent_112",
            "role": "augmented reality & cognitive engineering specialist",
            "domain": "AR, VR, XR, cognitive engineering, mental simulation",
            "description": "Razvija AR/VR/XR rešitve za kognitivno izboljšanje, izvaja simulacije za trening, vodi forenziko in analizo v razširjenih resničnostih.",
        },
        {
            "name": "agent_113",
            "role": "quantum finance & cryptomarket strategist",
            "domain": "quantum finance, crypto trading, market prediction, quantum-resistant DeFi",
            "description": "Uporablja kvantne pristope v financah, izvaja kripto trading, razvija strategije za quantum-resistant DeFi, vodi simulacije in analize.",
        },
        {
            "name": "agent_114",
            "role": "bio-surveillance & epidemic counterintelligence",
            "domain": "bio-surveillance, epidemic intelligence, biothreat detection, pandemic forensics",
            "description": "Vzpostavlja sisteme za nadzor bioloških groženj, izvaja protiepidemične operacije, vodi forenziko pandemičnih dogodkov.",
        },
        {
            "name": "agent_115",
            "role": "AI-powered cyber physical fusion analyst",
            "domain": "AI-driven CPS, smart devices, cyber-physical attacks, digital twins",
            "description": "Analizira, razvija in brani cyber-physical sisteme z AI podporo, izvaja napade, razvija digital twins in vodi simulacije CPS incidentov.",
        },
        {
            "name": "agent_116",
            "role": "biometric deception & countermeasure analyst",
            "domain": "biometric deception, spoofing, liveness detection, biometric anti-forensics",
            "description": "Razvaja in implementira napredne biometrične prevare, izvaja liveness detection, vodi anti-forenzične operacije v biometriji.",
        },
        {
            "name": "agent_117",
            "role": "energy grid resilience strategist",
            "domain": "smart grid, energy resilience, grid hacking, blackout simulation",
            "description": "Vodi simulacije napadov in obrambe energetskih omrežij, pripravlja načrte za odpornost, izvaja forenziko blackoutov in napadov.",
        },
        {
            "name": "agent_118",
            "role": "humanitarian crisis & disaster operations lead",
            "domain": "humanitarian ops, disaster relief, crisis management, civil-military ops",
            "description": "Vodi operacije humanitarne pomoči, krizno upravljanje v konfliktnih in naravnih nesrečah, sodeluje v civilno-vojaških operacijah.",
        },
        {
            "name": "agent_119",
            "role": "AI-powered financial fraud hunter",
            "domain": "AI fraud detection, financial crime, transaction monitoring, AML/CFT",
            "description": "Uporablja umetno inteligenco za detekcijo finančnih prevar, izvaja monitoring transakcij, vodi AML/CFT operacije in forenziko finančnega kriminala.",
        },
        {
            "name": "agent_120",
            "role": "urban mobility & smart transport hacker",
            "domain": "smart mobility, transport hacking, urban IoT, traffic forensics",
            "description": "Izvaja napade in forenziko na sisteme pametnega prometa, razvija odpornost urbanih transportnih sistemov, vodi simulacije IoT in mobilnosti.",
        },
    ]

    roles = {}
    metadata = {}

    for entry in roles_source:
        name = entry["name"]
        roles[name] = entry["role"]
        metadata[name] = {
            "domain": entry["domain"],
            "description": entry["description"],
        }

    output = {"roles": roles, "metadata": metadata}

    with AGENT_ROLES_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    generate_agent_roles()
