/* DigiByte Wallet newsroom: client-side localization and price widget.
   No geolocation, analytics fingerprinting, or external script libraries. */
(() => {
  'use strict';
  const locales = {
    en: {news:'News', home:'Home', features:'Features', getWallet:'Get the wallet', latest:'Latest news', library:'Developer library released', upcoming:'Wallet 0.1.5 is available', read:'Read the story', preview:'Explore what is coming', download:'Download for iPhone or Mac', apple:'Available on iPhone, iPad and compatible Apple-silicon Macs', price:'DGB market price', approximately:'Estimated price', refresh:'Updated', stale:'Price update delayed', unavailable:'Price unavailable', source:'Source', perDgb:'per DGB', currency:'Currency', language:'Language', detect:'Automatic', readEnglish:'Full articles are currently published in English.', aboutPrice:'Indicative market rate, not a purchase quote.', more:'More about this release'},
    es: {news:'Noticias', home:'Inicio', features:'Funciones', getWallet:'Obtener la cartera', latest:'Últimas noticias', library:'Nueva biblioteca para desarrolladores', upcoming:'La versión 0.1.5 ya está disponible', read:'Leer la noticia', preview:'Descubre lo que viene', download:'Descargar para iPhone o Mac', apple:'Para iPhone, iPad y Mac compatibles con chips Apple', price:'Precio de DGB', approximately:'Precio estimado', refresh:'Actualizado', stale:'Actualización retrasada', unavailable:'Precio no disponible', source:'Fuente', perDgb:'por DGB', currency:'Moneda', language:'Idioma', detect:'Automático', readEnglish:'Los artículos completos están disponibles en inglés.', aboutPrice:'Tipo de mercado indicativo, no oferta de compra.', more:'Más sobre esta versión'},
    fr: {news:'Actualités', home:'Accueil', features:'Fonctions', getWallet:'Obtenir le portefeuille', latest:'Dernières nouvelles', library:'Nouvelle bibliothèque développeur', upcoming:'La version 0.1.5 est disponible', read:'Lire l’article', preview:'Découvrir la prochaine version', download:'Télécharger pour iPhone ou Mac', apple:'Pour iPhone, iPad et Mac Apple Silicon compatibles', price:'Cours du DGB', approximately:'Prix estimé', refresh:'Actualisé', stale:'Mise à jour retardée', unavailable:'Cours indisponible', source:'Source', perDgb:'par DGB', currency:'Devise', language:'Langue', detect:'Automatique', readEnglish:'Les articles complets sont actuellement en anglais.', aboutPrice:'Cours indicatif, pas une offre d’achat.', more:'En savoir plus'},
    de: {news:'Neuigkeiten', home:'Startseite', features:'Funktionen', getWallet:'Wallet herunterladen', latest:'Aktuelles', library:'Entwicklerbibliothek veröffentlicht', upcoming:'Wallet 0.1.5 ist verfügbar', read:'Artikel lesen', preview:'Ausblick ansehen', download:'Für iPhone oder Mac laden', apple:'Für iPhone, iPad und kompatible Apple-Silicon-Macs', price:'DGB-Marktkurs', approximately:'Geschätzter Kurs', refresh:'Aktualisiert', stale:'Kursaktualisierung verzögert', unavailable:'Kurs nicht verfügbar', source:'Quelle', perDgb:'pro DGB', currency:'Währung', language:'Sprache', detect:'Automatisch', readEnglish:'Vollständige Artikel sind derzeit auf Englisch.', aboutPrice:'Unverbindlicher Marktkurs, kein Kaufangebot.', more:'Mehr erfahren'},
    pt: {news:'Notícias', home:'Início', features:'Recursos', getWallet:'Obter carteira', latest:'Últimas notícias', library:'Biblioteca para desenvolvedores lançada', upcoming:'A carteira 0.1.5 já está disponível', read:'Ler a notícia', preview:'Veja o que vem por aí', download:'Baixar para iPhone ou Mac', apple:'Para iPhone, iPad e Macs Apple Silicon compatíveis', price:'Preço de mercado DGB', approximately:'Preço estimado', refresh:'Atualizado', stale:'Atualização atrasada', unavailable:'Preço indisponível', source:'Fonte', perDgb:'por DGB', currency:'Moeda', language:'Idioma', detect:'Automático', readEnglish:'Os artigos completos estão disponíveis em inglês.', aboutPrice:'Cotação indicativa, não uma oferta de compra.', more:'Saiba mais'},
    it: {news:'Notizie', home:'Home', features:'Funzioni', getWallet:'Scarica il wallet', latest:'Ultime notizie', library:'Nuova libreria per sviluppatori', upcoming:'Wallet 0.1.5 disponibile', read:'Leggi la notizia', preview:'Scopri le novità', download:'Scarica per iPhone o Mac', apple:'Per iPhone, iPad e Mac Apple Silicon compatibili', price:'Prezzo DGB', approximately:'Prezzo indicativo', refresh:'Aggiornato', stale:'Aggiornamento in ritardo', unavailable:'Prezzo non disponibile', source:'Fonte', perDgb:'per DGB', currency:'Valuta', language:'Lingua', detect:'Automatico', readEnglish:'Gli articoli completi sono disponibili in inglese.', aboutPrice:'Quotazione indicativa, non un’offerta di acquisto.', more:'Scopri di più'},
    ja: {news:'ニュース', home:'ホーム', features:'機能', getWallet:'ウォレットを入手', latest:'最新ニュース', library:'開発者向けライブラリを公開', upcoming:'ウォレット0.1.5は配信中', read:'記事を読む', preview:'今後の更新を見る', download:'iPhoneまたはMacにダウンロード', apple:'iPhone、iPad、対応するAppleシリコンMac', price:'DGB参考価格', approximately:'参考価格', refresh:'更新', stale:'価格更新が遅れています', unavailable:'価格を取得できません', source:'情報源', perDgb:'/ DGB', currency:'通貨', language:'言語', detect:'自動', readEnglish:'記事の全文は現在英語で公開されています。', aboutPrice:'参考市場価格であり購入提示ではありません。', more:'詳細を見る'},
    hi: {news:'समाचार', home:'होम', features:'सुविधाएँ', getWallet:'वॉलेट डाउनलोड करें', latest:'नई खबरें', library:'डेवलपर लाइब्रेरी जारी', upcoming:'वॉलेट 0.1.5 उपलब्ध है', read:'खबर पढ़ें', preview:'आगामी बदलाव देखें', download:'iPhone या Mac के लिए डाउनलोड', apple:'iPhone, iPad और संगत Apple Silicon Mac', price:'DGB बाजार मूल्य', approximately:'अनुमानित मूल्य', refresh:'अपडेट', stale:'मूल्य अपडेट में देरी', unavailable:'मूल्य उपलब्ध नहीं', source:'स्रोत', perDgb:'प्रति DGB', currency:'मुद्रा', language:'भाषा', detect:'स्वचालित', readEnglish:'पूरे लेख फिलहाल अंग्रेज़ी में उपलब्ध हैं।', aboutPrice:'अनुमानित बाजार भाव, खरीद का प्रस्ताव नहीं।', more:'और जानें'},
    ar: {news:'الأخبار', home:'الرئيسية', features:'الميزات', getWallet:'الحصول على المحفظة', latest:'آخر الأخبار', library:'إصدار مكتبة المطورين', upcoming:'المحفظة 0.1.5 متاحة الآن', read:'اقرأ الخبر', preview:'اكتشف ما هو قادم', download:'التنزيل لـ iPhone أو Mac', apple:'لـ iPhone وiPad وأجهزة Mac المتوافقة', price:'سعر DGB', approximately:'السعر التقديري', refresh:'آخر تحديث', stale:'تأخر تحديث السعر', unavailable:'السعر غير متاح', source:'المصدر', perDgb:'لكل DGB', currency:'العملة', language:'اللغة', detect:'تلقائي', readEnglish:'المقالات الكاملة متاحة حاليًا باللغة الإنجليزية.', aboutPrice:'سعر سوق تقريبي وليس عرض شراء.', more:'التفاصيل'}
  };
  const currencies = ['USD','EUR','GBP','AUD','BRL','ARS','BDT','CNY','DKK','HRK','IDR','INR','IRR','JPY','KES','KRW','NOK','PHP','PKR','PLN','RON','RUB','SEK','THB','TRY','TZS','UAH','UGX','VND'];
  const currencyRegions = {US:'USD',CA:'USD',GB:'GBP',AU:'AUD',NZ:'AUD',FR:'EUR',DE:'EUR',ES:'EUR',IT:'EUR',NL:'EUR',BE:'EUR',IE:'EUR',PT:'EUR',AT:'EUR',FI:'EUR',GR:'EUR',BR:'BRL',AR:'ARS',BD:'BDT',CN:'CNY',DK:'DKK',HR:'EUR',ID:'IDR',IN:'INR',IR:'IRR',JP:'JPY',KE:'KES',KR:'KRW',NO:'NOK',PH:'PHP',PK:'PKR',PL:'PLN',RO:'RON',RU:'RUB',SE:'SEK',TH:'THB',TR:'TRY',TZ:'TZS',UA:'UAH',UG:'UGX',VN:'VND'};
  const langPicker=document.getElementById('news-language');
  const currencyPicker=document.getElementById('news-currency');
  const browserLocale=Array.isArray(navigator.languages)&&navigator.languages[0]?navigator.languages[0]:(navigator.language||'en-US');
  const safeStorage={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
  const baseLang=browserLocale.split('-')[0].toLowerCase();
  let lang=locales[safeStorage.get('dwnews-lang')]?safeStorage.get('dwnews-lang'):(locales[baseLang]?baseLang:'en');
  function regionOf(l){try{return new Intl.Locale(l).region||null}catch(e){return (l.split('-')[1]||'').toUpperCase()}}
  let currency=safeStorage.get('dwnews-currency');
  if(!currencies.includes(currency))currency=currencyRegions[regionOf(browserLocale)]||'USD';
  if(!currencies.includes(currency))currency='USD';
  const label=(key)=> (locales[lang]&&locales[lang][key]) || locales.en[key] || key;
  function translate(){
    document.documentElement.lang='en'; // Article body is English; do not mislabel it.
    document.querySelectorAll('[data-i18n]').forEach(el=>{const v=label(el.getAttribute('data-i18n'));if(v)el.textContent=v});
    if(langPicker)langPicker.value=lang;
    if(currencyPicker)currencyPicker.value=currency;
    document.querySelectorAll('[data-i18n-aria]').forEach(el=>el.setAttribute('aria-label',label(el.getAttribute('data-i18n-aria'))));
  }
  if(langPicker){langPicker.addEventListener('change',()=>{lang=langPicker.value;safeStorage.set('dwnews-lang',lang);translate();displayPrice();});}
  if(currencyPicker){
    currencies.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;currencyPicker.appendChild(o)});
    currencyPicker.addEventListener('change',()=>{currency=currencyPicker.value;safeStorage.set('dwnews-currency',currency);displayPrice()});
  }
  let data=null;
  function money(value){
    try{return new Intl.NumberFormat(browserLocale,{style:'currency',currency,minimumFractionDigits:2,maximumFractionDigits:value<.01?8:5}).format(value)}
    catch(e){return value.toFixed(6)+' '+currency}
  }
  function dateTime(iso){try{return new Intl.DateTimeFormat(browserLocale,{dateStyle:'medium',timeStyle:'short'}).format(new Date(iso))}catch(e){return iso}}
  function displayPrice(){
    const val=document.getElementById('dgb-price-value'),state=document.getElementById('dgb-price-state'), source=document.getElementById('dgb-price-source');
    if(!val)return;
    if(!data||!data.prices||!(Number(data.prices.DGB)>0)){
      val.textContent='—'; if(state)state.textContent=label('unavailable'); if(source)source.textContent=label('aboutPrice');return;
    }
    const exchange=currency==='USD'?1:Number(data.prices[currency]);
    if(!Number.isFinite(exchange)||exchange<=0){val.textContent='—';state.textContent=label('unavailable');return;}
    const ts=data.status && (data.status.completedAt||data.status.startedAt);
    const age=ts?Date.now()-Date.parse(ts):Infinity;
    const staleSymbols=data.status&&data.status.cryptoStaleSymbols||[];
    const fiatTs=data.status&&data.status.lastFiatRefreshAt;
    const fiatAge=fiatTs?Date.now()-Date.parse(fiatTs):Infinity;
    const stale=!Number.isFinite(age)||age< -300000||age>15*60*1000||staleSymbols.includes('DGB')||(currency!=='USD'&&(!Number.isFinite(fiatAge)||fiatAge>24*3600000));
    // Do not present cached or explicitly stale quotes as live.
    if(stale){val.textContent='—';state.textContent=label('stale');}
    else {val.textContent=money(Number(data.prices.DGB)*exchange);state.textContent=label('refresh')+': '+dateTime(ts);}
    if(source)source.textContent=label('source')+': '+((data.status&&data.status.sources&&data.status.sources.DGB)||'Market data')+' · '+label('aboutPrice');
  }
  async function loadPrice(){
    const urls=['/news/data/dgb-price.json?at='+Date.now(),'https://price-update.totality.workers.dev/'];
    let lastCandidate=null;
    for(const url of urls){
      try{
        const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),6500);
        let resp;
        try{resp=await fetch(url,{cache:'no-store',signal:controller.signal,credentials:'omit'})}finally{clearTimeout(timer)}
        if(!resp.ok)continue;
        const candidate=await resp.json();
        if(candidate.ok===true && candidate.prices && Number(candidate.prices.DGB)>0){
          lastCandidate=candidate;
          const ts=candidate.status&&(candidate.status.completedAt||candidate.status.startedAt);
          const age=ts?Date.now()-Date.parse(ts):Infinity;
          if(Number.isFinite(age) && age>=-300000 && age<15*60*1000){data=candidate;displayPrice();return;}
        }
      }catch(e){}
    }
    if(lastCandidate)data=lastCandidate;
    displayPrice();
  }
  translate(); displayPrice(); loadPrice();
  setInterval(loadPrice,120000);
  document.querySelectorAll('[data-copy-link]').forEach(b=>b.addEventListener('click',()=>{
    if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(location.href).then(()=>{b.textContent='Link copied';setTimeout(()=>{b.textContent='Copy link'},1800)}).catch(()=>{});
  }));
})();

/* News V3.1: conservative responsive price sizing and opt-in genuine AdSense slots. */
(() => {
  'use strict';
  const val = document.getElementById('dgb-price-value');
  function fit() {
    if (!val) return;
    val.style.removeProperty('font-size');
    if (!val.textContent || val.textContent.trim() === '—') return;
    const room = val.clientWidth;
    if (room < 20) return;
    let px = parseFloat(getComputedStyle(val).fontSize) || 32;
    for (let i=0; i<7 && val.scrollWidth > room + 1 && px > 16; i++) {
      px = Math.max(16, Math.floor(px * (room / Math.max(val.scrollWidth, 1)) * 0.97));
      val.style.setProperty('font-size', px + 'px', 'important');
    }
  }
  if (val) {
    new MutationObserver(() => requestAnimationFrame(fit)).observe(val,{childList:true,subtree:true,characterData:true});
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(fit).observe(val.parentElement);
    requestAnimationFrame(fit);
  }
  const all = [...document.querySelectorAll('.dw-ad-target[data-ad-zone]')];
  if (!all.length) return;
  fetch('/news/assets/ads-config.json',{cache:'no-store',credentials:'omit'})
    .then(r=>r.ok?r.json():{})
    .then(cfg=>{
      const client='ca-pub-1492791099222955';
      for (const holder of all) {
        const slot=String(cfg[holder.dataset.adZone]||'');
        if (!/^[0-9]{5,20}$/.test(slot)) continue;
        holder.classList.add('is-active');
        const ins=document.createElement('ins');
        ins.className='adsbygoogle';
        ins.style.display='block';
        ins.setAttribute('data-ad-client',client);
        ins.setAttribute('data-ad-slot',slot);
        ins.setAttribute('data-ad-format','auto');
        ins.setAttribute('data-full-width-responsive','true');
        holder.appendChild(ins);
        try {(window.adsbygoogle=window.adsbygoogle||[]).push({});}catch(_e){}
      }
    }).catch(()=>{});
})();
