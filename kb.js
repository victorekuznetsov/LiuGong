/* База знаний LiuGong внутри каталога запасных частей.

   Сделана по образцу базы знаний Cummins: те же разделы, те же крошки,
   те же карточки и тот же адрес вида `#/part/<номер>`. Данные лежат в
   `data/kb_*.js`, паспорта деталей грузятся шардами по мере надобности,
   поэтому база работает и с диска, без сервера.

   Чего здесь нет и почему. У Cummins ядро базы — документы QuickServe:
   процедуры ремонта, TSB, сервисные бюллетени с полными текстами. В EPC
   LiuGong документов нет вовсе — портал отдаёт каталог, паспорта деталей
   и фотографии. Поэтому раздела документов здесь не заведено: пустой
   раздел обещал бы то, чего нет. Вместо него — паспорта, фотографии,
   цепочки замен и темы, собранные по самим деталям. */
(function () {
"use strict";

var PARTS = window.KB_PARTS || {};
var TOPICS = window.KB_TOPICS || [];
var MACHINES = window.KB_MACHINES || {};
var META = window.KB_META || {};
var BOOKS = window.BOOKS || [];
var FLEET = window.FLEET || [];
var CODES = window.CODES || {};

var byCode = {};
BOOKS.forEach(function (b) { byCode[b.code] = b; });

var root = document.getElementById("kb-root");
var LANG = "ru";
try { LANG = localStorage.getItem("liugong_lang") || "ru"; } catch (e) {}

/* --------------------------------------------------------------- утилиты */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}
function norm(s) {
  return String(s == null ? "" : s).toUpperCase()
    .replace(/[АВЕКМНОРСТУХ]/g, function (c) {
      return "ABEKMHOPCTYX".charAt("АВЕКМНОРСТУХ".indexOf(c));
    })
    .replace(/[^0-9A-Z]/g, "");
}
function num(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " "); }
function plural(n, one, few, many) {
  var a = Math.abs(n) % 100, b = a % 10;
  if (a > 10 && a < 20) return many;
  if (b > 1 && b < 5) return few;
  if (b === 1) return one;
  return many;
}
function money(v) { return num(Math.round(v)) + " ₽"; }

/* Рекомендация EPC по запасу приходит по-английски и всего семью
   значениями; в данных она остаётся как её написал завод. */
var STORE_RU = {
  "not recommend": "не рекомендуется", "1 year": "1 год", "2 years": "2 года",
  "3 years": "3 года", "5 years": "5 лет", "1000h": "1000 ч", "500h": "500 ч"
};
function storeRu(v) {
  return STORE_RU[String(v || "").trim().toLowerCase()] || v;
}

/* Наименование на выбранном языке. Опись хранит все три сразу:
   [русское, английское, китайское, применений, признаки]. */
function title(no) {
  var p = PARTS[no];
  if (!p) return "";
  if (LANG === "zh") return p[2] || p[1] || p[0] || "";
  if (LANG === "en") return p[1] || p[0] || "";
  return p[0] || p[1] || "";
}
function subtitle(no) {
  var p = PARTS[no];
  if (!p) return "";
  var main = title(no);
  var rest = [p[0], p[1], p[2]].filter(function (x) { return x && x !== main; });
  return rest.join(" · ");
}
function partLink(no, label) {
  if (!PARTS[no]) return esc(label || no);
  return '<a class="lnk part" href="#/part/' + encodeURIComponent(no) + '">' +
    esc(label || no) + "</a>";
}
function bookLink(code) {
  var b = byCode[code];
  return '<a class="lnk" href="#/machine/' + encodeURIComponent(code) + '">' +
    esc(b ? b.model + " · " + code : code) + "</a>";
}
function crumbs(list) {
  return '<div class="crumbs">' + list.map(function (c, i) {
    var t = c.href ? '<a href="' + c.href + '">' + esc(c.t) + "</a>"
                   : '<span class="cur">' + esc(c.t) + "</span>";
    return (i ? "<i>›</i>" : "") + t;
  }).join("") + "</div>";
}
function render(html) {
  root.innerHTML = html;
  window.scrollTo(0, 0);
  markNav();
}
function markNav() {
  var nav = document.getElementById("kb-nav");
  if (!nav) return;
  Array.prototype.forEach.call(nav.querySelectorAll("a"), function (a) {
    var h = a.getAttribute("href");
    a.classList.toggle("on", h && h.charAt(0) === "#" &&
      location.hash.indexOf(h) === 0);
  });
}
function notFound(what) {
  render(crumbs([{ t: "База знаний", href: "#/kb" }, { t: "Не найдено" }]) +
    '<section class="kb-card"><h2>' + esc(what) + "</h2>" +
    '<p class="sub">В базе такого нет.</p></section>');
}

/* ------------------------------------------------------- подгрузка данных */
window.__DATA__ = window.__DATA__ || {};
var pending = {};

function loadScript(key, url) {
  if (Object.prototype.hasOwnProperty.call(window.__DATA__, key)) {
    return Promise.resolve(window.__DATA__[key]);
  }
  if (pending[url]) return pending[url];
  pending[url] = new Promise(function (resolve, reject) {
    var el = document.createElement("script");
    el.src = url;
    el.onload = function () {
      if (Object.prototype.hasOwnProperty.call(window.__DATA__, key)) {
        resolve(window.__DATA__[key]);
      } else { reject(new Error(url)); }
    };
    el.onerror = function () { reject(new Error(url)); };
    document.head.appendChild(el);
  });
  return pending[url];
}

var info = {}, supply = {};

function loadPart(no) {
  var k = norm(no).slice(0, 2) || "__";
  return Promise.all([
    loadScript("p:" + k, "data/kb/p-" + k + ".js").catch(function () { return {}; }),
    loadScript("sup:" + k, "data/supply/s-" + k + ".js").catch(function () { return {}; })
  ]).then(function (r) {
    Object.keys(r[0]).forEach(function (x) { info[x] = r[0][x]; });
    Object.keys(r[1]).forEach(function (x) { supply[x] = r[1][x]; });
  });
}
function loadIndex(no) {
  var k = norm(no).slice(0, 2) || "__";
  return loadScript("idx:" + k, "data/index/parts-" + k + ".js")
    .catch(function () { return {}; });
}
function loadTree(code) {
  return loadScript("tree:" + code, "data/" + code + "/tree.js");
}
function loadUnit(code, id) {
  return loadScript("u:" + code + "/" + id, "data/" + code + "/u/" + id + ".js");
}

/* ------------------------------------------------------------- стартовая */
function viewHome() {
  var h = [];
  h.push('<div class="kb-hero"><h1>База знаний LiuGong</h1>' +
    '<p class="lead">Паспорта деталей из EPC LiuGong, фотографии, цепочки замен, ' +
    'цены по прайс-листу, разделы каталогов и парк машин АО «Полюс» — со ' +
    'сквозными перекрёстными ссылками: деталь → узел → машина → парк.</p>' +
    '<div class="kb-counters">' +
    [["Деталей", META.parts || Object.keys(PARTS).length, "#/parts"],
     ["Паспортов", META.passports || 0, "#/parts"],
     ["С фотографиями", META.photos || 0, "#/parts"],
     ["С ценой", META.priced || 0, "#/parts"],
     ["С цепочкой замен", META.chains || 0, "#/parts"],
     ["Машин каталога", META.machines || Object.keys(MACHINES).length, "#/machines"],
     ["Машин в парке", FLEET.length, "#/fleet"],
     ["Тем", TOPICS.length, "#/topics"]
    ].map(function (c) {
      return '<a class="counter" href="' + c[2] + '"><b>' + num(c[1]) +
        "</b><span>" + esc(c[0]) + "</span></a>";
    }).join("") + "</div></div>");

  h.push('<div class="kb-cols">');

  h.push('<section class="kb-card"><h2>С чего начать</h2><table class="kb-table">' +
    [["Найти деталь по номеру", "поле поиска в шапке — работает и с кириллическими двойниками"],
     ["Найти деталь по названию", "поиск понимает русское, английское и китайское наименование"],
     ["Узнать, куда деталь ставится", "карточка детали → «Где применяется»"],
     ["Посмотреть чертёж узла", "ссылка «открыть в каталоге» в карточке узла"],
     ["Понять, чем заменена деталь", "карточка детали → «Замены и состояние номера»"],
     ["Собрать список на ТО", "тема «Детали технического обслуживания»"],
     ["Найти машину по VIN", "раздел «Парк»"]
    ].map(function (r) {
      return "<tr><td>" + esc(r[0]) + '</td><td class="sub">' + esc(r[1]) + "</td></tr>";
    }).join("") + "</table></section>");

  h.push('<section class="kb-card"><h2>Машины <span class="cnt">' +
    Object.keys(MACHINES).length + "</span></h2><ul class=\"kb-list\">");
  Object.keys(MACHINES).forEach(function (code) {
    var m = MACHINES[code];
    var n = FLEET.filter(function (f) { return f.books.indexOf(code) >= 0; }).length;
    h.push('<li><a href="#/machine/' + encodeURIComponent(code) + '">' +
      esc(m.model) + "</a>" + (m.kind ? " — " + esc(m.kind) : "") +
      '<span class="sub">разделов ' + m.ch.length + " · в парке " + n + " " +
      plural(n, "машина", "машины", "машин") + "</span></li>");
  });
  h.push("</ul></section>");

  h.push('<section class="kb-card"><h2>Темы <span class="cnt">' + TOPICS.length +
    "</span></h2><ul class=\"kb-list\">");
  TOPICS.forEach(function (t, i) {
    h.push('<li><a href="#/topic/' + i + '">' + esc(t.t) + '</a> <span class="cnt">' +
      t.ids.length + '</span><span class="sub">' + esc(t.d) + "</span></li>");
  });
  h.push("</ul></section>");

  h.push('<section class="kb-card wide"><h2>Чего в базе нет</h2>' +
    '<p class="sub">Руководств по ремонту, сервисных бюллетеней и процедур ' +
    'здесь нет: портал EPC LiuGong их не отдаёт — он отдаёт каталог, ' +
    'паспорта деталей и фотографии. В базе знаний Cummins, сделанной по ' +
    'той же схеме, этот раздел есть, потому что его отдаёт QuickServe. ' +
    'Заводить пустой раздел ради сходства незачем: он обещал бы то, чего ' +
    'в выгрузке нет.</p></section>');

  h.push("</div>");
  render(h.join(""));
}

/* ---------------------------------------------------------------- детали */
function viewParts(q) {
  var ids = Object.keys(PARTS).sort();
  var h = [crumbs([{ t: "База знаний", href: "#/kb" }, { t: "Детали" }])];
  h.push('<div class="kb-head"><h1>Детали <span class="cnt">' + num(ids.length) +
    '</span></h1><input class="kb-filter" id="kb-filter" ' +
    'placeholder="Номер или наименование…" value="' + esc(q || "") + '">' +
    '<p class="lead">Номер, наименование на трёх языках и сколько раз деталь ' +
    'встречается в составах узлов. Щелчок по номеру открывает карточку.</p>' +
    '</div><div id="kb-plist"></div>');
  render(h.join(""));

  function rows(f) {
    f = (f || "").trim().toLowerCase();
    var key = norm(f);
    var out = [], n = 0;
    for (var i = 0; i < ids.length && n < 600; i++) {
      var no = ids[i], p = PARTS[no];
      if (f) {
        var hay = (p[0] + " " + p[1] + " " + p[2]).toLowerCase();
        if (hay.indexOf(f) === -1 && (!key || norm(no).indexOf(key) === -1)) continue;
      }
      n++;
      out.push("<tr><td class='c-id'>" + partLink(no) + "</td><td>" +
        esc(title(no)) + '<span class="sub"> ' + esc(subtitle(no)) + "</span></td>" +
        "<td class='c-eng'>" + marks(p[4]) + "</td>" +
        "<td class='c-date'>" + (p[3] ? p[3] + " прим." : "") + "</td></tr>");
    }
    if (!out.length) return '<p class="empty">Ничего не найдено.</p>';
    return '<table class="kb-table">' + out.join("") + "</table>" +
      (n >= 600 ? '<p class="sub">Показаны первые 600 — уточните фильтр.</p>' : "");
  }
  var box = document.getElementById("kb-plist");
  box.innerHTML = rows(q);
  var inp = document.getElementById("kb-filter");
  inp.oninput = function () {
    var v = this.value;
    clearTimeout(inp._t);
    inp._t = setTimeout(function () {
      location.replace("#/parts/" + encodeURIComponent(v));
      box.innerHTML = rows(v);
    }, 180);
  };
}

var MARK = [[1, "ТО", "деталь технического обслуживания"],
            [2, "изн.", "быстроизнашивающаяся"],
            [4, "спец.", "особый заказ"],
            [8, "фото", "есть фотография"],
            [16, "цена", "есть в прайс-листе"],
            [32, "снята", "снята с производства"],
            [64, "замена", "есть цепочка замен"]];

function marks(f) {
  return MARK.filter(function (m) { return (f || 0) & m[0]; })
    .map(function (m) {
      return '<span class="chip" title="' + esc(m[2]) + '">' + esc(m[1]) + "</span>";
    }).join(" ");
}

function viewPart(no) {
  if (!PARTS[no]) {
    // номер мог прийти из каталога в другом написании
    var want = norm(no), found = null;
    Object.keys(PARTS).some(function (k) {
      if (norm(k) === want) { found = k; return true; }
      return false;
    });
    if (found) { location.replace("#/part/" + encodeURIComponent(found)); return; }
    notFound("Деталь " + no);
    return;
  }
  Promise.all([loadPart(no), loadIndex(no)]).then(function (r) {
    var idx = r[1] || {};
    var hits = (idx[norm(no)] || []);
    var d = info[no] || {};
    var s = supply[no] || {};
    var h = [crumbs([{ t: "База знаний", href: "#/kb" },
                     { t: "Детали", href: "#/parts" }, { t: no }])];
    h.push('<div class="kb-head"><h1>' + esc(no) + "</h1>" +
      '<p class="lead">' + esc(title(no)) +
      (subtitle(no) ? ' <span class="sub">' + esc(subtitle(no)) + "</span>" : "") +
      "</p></div>");

    h.push('<div class="kb-cols">');

    var rows = [
      ["Наименование, русское", d.ru || PARTS[no][0]],
      ["Наименование, английское", d.en || PARTS[no][1]],
      ["Наименование, китайское", d.zh || PARTS[no][2]],
      ["Обозначение", d.spec],
      ["Масса, кг", d.kg],
      ["Габариты, мм", d.mm],
      ["Минимальная партия", d.mpq],
      ["Группа скидки", d.dg],
      ["Рекомендация по запасу", storeRu(d.stock)],
      ["Единица", d.unit],
      ["Примечание завода", d.note]
    ].filter(function (r) { return r[1]; });
    h.push('<section class="kb-card"><h2>Паспорт</h2>' +
      '<table class="kb-table">' + rows.map(function (r) {
        return "<tr><th>" + esc(r[0]) + "</th><td>" + esc(r[1]) + "</td></tr>";
      }).join("") + "</table>" +
      '<p class="sub">' + marks(PARTS[no][4]) + "</p>" +
      (d.up ? '<p class="sub">Входит в сборку ' + partLink(d.up) + ".</p>" : "") +
      "</section>");

    if (d.ph && d.ph.length) {
      h.push('<section class="kb-card"><h2>Фотографии <span class="cnt">' +
        d.ph.length + '</span></h2><div class="part-photos">' +
        d.ph.map(function (src) {
          return '<img src="' + esc(src) + '" alt="' + esc(no) + '" loading="lazy">';
        }).join("") + "</div></section>");
    }

    if (s.p) {
      h.push('<section class="kb-card"><h2>Цена по прайс-листу</h2>' +
        '<table class="kb-table"><tr><th>Базис</th><th>рублей без НДС</th></tr>' +
        (s.p.b1 != null ? "<tr><td>Магадан, Алдан, Хабаровск</td><td>" +
          money(s.p.b1) + "</td></tr>" : "") +
        (s.p.b2 != null ? "<tr><td>Лесосибирск, Таксимо, Новосибирск</td><td>" +
          money(s.p.b2) + "</td></tr>" : "") +
        "</table>" +
        (s.p.n ? '<p class="sub">В прайсе записана как «' + esc(s.p.n) + "».</p>" : "") +
        "</section>");
    }

    if ((s.c && s.c.length) || (s.f && s.f.length)) {
      h.push('<section class="kb-card"><h2>Замены и состояние номера</h2>');
      (s.f || []).forEach(function (code) {
        var c = CODES[code] || {};
        h.push('<p class="sub"><b>' + esc(c.s || code) + "</b> — " +
          esc(c.f || "") + "</p>");
      });
      if (s.c && s.c.length) {
        h.push('<table class="kb-table">');
        s.c.forEach(function (l) {
          var c = CODES[l.code] || {};
          var no = l.d || l.n;
          h.push("<tr><td class='c-id'>" +
            (l.x ? esc(no) : partLink(no)) + "</td><td>" +
            esc(c.s || l.code) + '<span class="sub"> ' + esc(c.f || "") +
            (l.x ? " · в каталоге этого номера нет" : "") + "</span></td></tr>");
        });
        h.push("</table>");
      }
      if (s.note) h.push('<p class="sub">Как это записано в EPC: «' + esc(s.note) + "».</p>");
      h.push("</section>");
    }

    h.push('<section class="kb-card wide"><h2>Где применяется <span class="cnt">' +
      hits.length + "</span></h2>");
    if (!hits.length) {
      h.push('<p class="sub">В составах узлов этот номер не встречается — ' +
        "он пришёл из паспорта или из цепочки замен.</p>");
    } else {
      var byBook = {};
      hits.forEach(function (x) { (byBook[x[0]] = byBook[x[0]] || []).push(x); });
      h.push('<table class="kb-table"><thead><tr><th>Машина</th><th>Узел</th>' +
        "<th>Поз.</th><th></th></tr></thead><tbody>");
      Object.keys(byBook).sort().forEach(function (code) {
        byBook[code].forEach(function (x) {
          h.push("<tr><td>" + bookLink(code) + "</td>" +
            '<td><a class="lnk" href="#/unit/' + encodeURIComponent(code) + "/" +
            encodeURIComponent(x[1]) + '">' + esc(x[1]) + "</a></td>" +
            "<td class='c-date'>" + esc(x[2]) + "</td>" +
            '<td class="c-ext"><a class="lnk" href="index.html" data-catalog="' +
            esc(code) + "|" + esc(x[1]) + "|" + esc(no) +
            '">открыть в каталоге →</a></td></tr>');
        });
      });
      h.push("</tbody></table>");
    }
    h.push("</section></div>");
    render(h.join(""));
  });
}

/* ----------------------------------------------------------------- узлы */
function viewUnit(code, id) {
  var b = byCode[code];
  if (!b) { notFound("Машина " + code); return; }
  Promise.all([loadTree(code), loadUnit(code, id)]).then(function (r) {
    var page = r[1];
    var parts = page.rows.map(function (x) { return x[1]; }).filter(Boolean);
    return loadPartsFor(parts).then(function () {
      var h = [crumbs([{ t: "База знаний", href: "#/kb" },
                       { t: "Машины", href: "#/machines" },
                       { t: b.model, href: "#/machine/" + encodeURIComponent(code) },
                       { t: page.t || id }])];
      h.push('<div class="kb-head"><h1>' + esc(page.t || id) + "</h1>" +
        '<p class="lead">' + esc(b.model) + " · узел " + esc(id) +
        (page.r ? " · номер сборки " + esc(page.r) : "") +
        (page.d ? " · редакция от " + esc(page.d) : "") + "</p></div>");
      h.push('<section class="kb-card wide"><h2>Состав <span class="cnt">' +
        page.rows.length + "</span> " +
        '<a class="btn-mini" href="index.html" data-catalog="' + esc(code) + "|" +
        esc(id) + '|">открыть чертёж в каталоге →</a></h2>' +
        '<table class="kb-table"><thead><tr><th>Поз.</th><th>Номер</th>' +
        "<th>Наименование</th><th>Кол-во</th><th>Примечание</th></tr></thead><tbody>");
      page.rows.forEach(function (x) {
        h.push("<tr><td class='c-date'>" + esc(x[0] || "") + "</td>" +
          "<td class='c-id'>" + (x[1] ? partLink(x[1]) : "") + "</td><td>" +
          esc(x[1] && PARTS[x[1]] ? title(x[1]) : (x[2] || "")) + "</td>" +
          "<td class='c-date'>" + esc(x[3] || "") + "</td>" +
          '<td class="sub">' + esc(x[4] || "") + "</td></tr>");
      });
      h.push("</tbody></table></section>");
      render(h.join(""));
    });
  }).catch(function () { notFound("Узел " + id); });
}

function loadPartsFor(list) {
  var keys = {};
  list.forEach(function (p) { keys[norm(p).slice(0, 2) || "__"] = 1; });
  return Promise.all(Object.keys(keys).map(function (k) {
    return loadScript("p:" + k, "data/kb/p-" + k + ".js")
      .then(function (s) { Object.keys(s).forEach(function (x) { info[x] = s[x]; }); })
      .catch(function () {});
  }));
}

/* --------------------------------------------------------------- машины */
function viewMachines() {
  var h = [crumbs([{ t: "База знаний", href: "#/kb" }, { t: "Машины" }])];
  h.push('<div class="kb-head"><h1>Машины каталога <span class="cnt">' +
    Object.keys(MACHINES).length + "</span></h1>" +
    '<p class="lead">Каждый каталог выкачан из EPC по VIN конкретной машины: ' +
    'у LiuGong книга сделана не на серию, а на исполнение (materialNo).</p></div>');
  h.push('<div class="kb-cols">');
  Object.keys(MACHINES).forEach(function (code) {
    var m = MACHINES[code], b = byCode[code] || {};
    h.push('<section class="kb-card"><h2><a href="#/machine/' +
      encodeURIComponent(code) + '">' + esc(m.model) + "</a></h2>" +
      '<p class="sub">' + esc(m.kind || "") + (m.line ? " · " + esc(m.line) : "") +
      "</p><table class=\"kb-table\">" +
      "<tr><th>Исполнение</th><td>" + esc(code) + "</td></tr>" +
      "<tr><th>VIN выгрузки</th><td>" + esc(m.vin || "—") + "</td></tr>" +
      "<tr><th>Разделов</th><td>" + m.ch.length + "</td></tr>" +
      "<tr><th>Узлов</th><td>" + num(b.units || 0) + "</td></tr>" +
      "<tr><th>Позиций</th><td>" + num(b.lines || 0) + "</td></tr>" +
      "<tr><th>Номеров</th><td>" + num(b.numbers || 0) + "</td></tr>" +
      "</table></section>");
  });
  h.push("</div>");
  render(h.join(""));
}

function viewMachine(code) {
  var m = MACHINES[code];
  if (!m) { notFound("Машина " + code); return; }
  var b = byCode[code] || {};
  var fleet = FLEET.filter(function (f) { return f.books.indexOf(code) >= 0; });
  loadTree(code).then(function (tree) {
    var h = [crumbs([{ t: "База знаний", href: "#/kb" },
                     { t: "Машины", href: "#/machines" }, { t: m.model }])];
    h.push('<div class="kb-head"><h1>' + esc(m.model) + "</h1>" +
      '<p class="lead">' + esc(m.kind || "") + " · исполнение " + esc(code) +
      (m.vin ? " · выкачан по VIN " + esc(m.vin) : "") +
      ' <a class="btn-mini" href="index.html" data-catalog="' + esc(code) +
      '||">открыть каталог →</a></p></div>');
    h.push('<div class="kb-cols">');

    h.push('<section class="kb-card wide"><h2>Разделы каталога <span class="cnt">' +
      tree.length + "</span></h2><ul class=\"kb-list cols\">");
    tree.forEach(function (sec) {
      var zh = (m.ch.filter(function (c) { return c.code === sec.id; })[0] || {}).zh || "";
      h.push('<li><a href="#/section/' + encodeURIComponent(code) + "/" +
        encodeURIComponent(sec.id) + '">' + esc(sec.title || sec.id) + "</a>" +
        '<span class="cnt">' + (sec.kids || []).length + "</span>" +
        (zh ? '<span class="sub">' + esc(zh) + "</span>" : "") + "</li>");
    });
    h.push("</ul></section>");

    if (m.spec) {
      h.push('<section class="kb-card wide"><h2>Исполнение как его пишет завод</h2>' +
        '<p class="sub">' + esc(m.spec) + "</p></section>");
    }

    h.push('<section class="kb-card wide"><h2>Машины парка на этом каталоге ' +
      '<span class="cnt">' + fleet.length + "</span></h2>");
    if (!fleet.length) {
      h.push('<p class="sub">В выгрузке парка машин этой модели нет.</p>');
    } else {
      h.push('<table class="kb-table"><thead><tr><th>Предприятие</th><th>Машина</th>' +
        "<th>VIN</th><th>Гар. №</th><th>Год</th><th>Привязка</th></tr></thead><tbody>");
      fleet.forEach(function (f) { h.push(fleetRow(f)); });
      h.push("</tbody></table>");
    }
    h.push("</section></div>");
    render(h.join(""));
  }).catch(function () { notFound("Машина " + code); });
}

function viewSection(code, secId) {
  loadTree(code).then(function (tree) {
    var sec = tree.filter(function (s) { return String(s.id) === String(secId); })[0];
    if (!sec) { notFound("Раздел " + secId); return; }
    var b = byCode[code] || {};
    var h = [crumbs([{ t: "База знаний", href: "#/kb" },
                     { t: "Машины", href: "#/machines" },
                     { t: b.model || code, href: "#/machine/" + encodeURIComponent(code) },
                     { t: sec.title || secId }])];
    h.push('<div class="kb-head"><h1>' + esc(sec.title || secId) + "</h1>" +
      '<p class="lead">' + esc(b.model || code) + " · раздел " + esc(secId) + "</p></div>");
    h.push('<section class="kb-card wide"><h2>Узлы</h2><ul class="kb-list">');
    (function walk(nodes, depth) {
      nodes.forEach(function (n) {
        h.push('<li style="padding-left:' + (depth * 14) + 'px">' +
          (n.g ? '<a href="#/unit/' + encodeURIComponent(code) + "/" +
            encodeURIComponent(n.id) + '">' + esc(n.title || n.id) + "</a>"
           : esc(n.title || n.id)) +
          (n.ref ? '<span class="sub">сборка ' + esc(n.ref) +
            (n.d ? " · редакция от " + esc(n.d) : "") + "</span>" : "") + "</li>");
        if (n.kids) walk(n.kids, depth + 1);
      });
    })(sec.kids || [], 0);
    h.push("</ul></section>");
    render(h.join(""));
  }).catch(function () { notFound("Раздел " + secId); });
}

/* ----------------------------------------------------------------- парк */
function fleetRow(f) {
  var note = f.fit === "vin" ? "каталог по этому VIN"
    : f.fit === "model" ? "каталог той же модели" : "каталога нет";
  return "<tr><td>" + esc(f.be) + "</td><td>" + esc(f.name || f.model) + "</td>" +
    "<td class='c-id'>" + esc(f.sn || "—") + "</td>" +
    "<td class='c-date'>" + esc(f.garage || "") + "</td>" +
    "<td class='c-date'>" + esc(f.year || "") + "</td>" +
    '<td><span class="fit fit-' + esc(f.fit) + '">' + esc(note) + "</span>" +
    (f.books.length ? " " + bookLink(f.books[0]) : "") + "</td></tr>";
}

function viewFleet() {
  var h = [crumbs([{ t: "База знаний", href: "#/kb" }, { t: "Парк" }])];
  var withBook = FLEET.filter(function (f) { return f.books.length; }).length;
  var exact = FLEET.filter(function (f) { return f.fit === "vin"; }).length;
  h.push('<div class="kb-head"><h1>Парк LiuGong АО «Полюс» <span class="cnt">' +
    FLEET.length + "</span></h1>" +
    '<p class="lead">Каталог есть у ' + withBook + " " +
    plural(withBook, "машины", "машин", "машин") + ", из них выкачано по своему VIN — " +
    exact + ". Разница существенная: у LiuGong каталог сделан на исполнение " +
    "машины, и у другой машины той же модели состав может отличаться.</p></div>");
  var sites = {};
  FLEET.forEach(function (f) { sites[f.be] = (sites[f.be] || 0) + 1; });
  h.push('<section class="kb-card wide"><h2>Машины</h2>' +
    '<table class="kb-table"><thead><tr><th>Предприятие</th><th>Машина</th>' +
    "<th>VIN</th><th>Гар. №</th><th>Год</th><th>Привязка</th></tr></thead><tbody>");
  FLEET.slice().sort(function (a, b) {
    return (a.be + a.model + a.garage).localeCompare(b.be + b.model + b.garage);
  }).forEach(function (f) { h.push(fleetRow(f)); });
  h.push("</tbody></table></section>");
  render(h.join(""));
}

/* ----------------------------------------------------------------- темы */
function viewTopics() {
  var h = [crumbs([{ t: "База знаний", href: "#/kb" }, { t: "Темы" }])];
  h.push('<div class="kb-head"><h1>Темы <span class="cnt">' + TOPICS.length +
    "</span></h1>" +
    '<p class="lead">Полки, с которых чаще всего снимают: детали собраны по ' +
    'назначению — по наименованию из каталога — и по заводским отметкам EPC ' +
    '(деталь ТО, быстроизнашивающаяся, снята с производства).</p></div>');
  h.push('<div class="kb-cols">');
  TOPICS.forEach(function (t, i) {
    h.push('<section class="kb-card"><h2><a href="#/topic/' + i + '">' +
      esc(t.t) + '</a> <span class="cnt">' + num(t.ids.length) + "</span></h2>" +
      '<p class="sub">' + esc(t.d) + "</p></section>");
  });
  h.push("</div>");
  render(h.join(""));
}

function viewTopic(i) {
  var t = TOPICS[i];
  if (!t) { notFound("Тема"); return; }
  var h = [crumbs([{ t: "База знаний", href: "#/kb" },
                   { t: "Темы", href: "#/topics" }, { t: t.t }])];
  h.push('<div class="kb-head"><h1>' + esc(t.t) + ' <span class="cnt">' +
    num(t.ids.length) + "</span></h1><p class=\"lead\">" + esc(t.d) + "</p></div>");
  h.push('<section class="kb-card wide"><table class="kb-table">');
  t.ids.slice(0, 800).forEach(function (no) {
    h.push("<tr><td class='c-id'>" + partLink(no) + "</td><td>" + esc(title(no)) +
      '<span class="sub"> ' + esc(subtitle(no)) + "</td><td class='c-eng'>" +
      marks((PARTS[no] || [])[4]) + "</td></tr>");
  });
  h.push("</table>");
  if (t.ids.length > 800) {
    h.push('<p class="sub">Показаны первые 800 из ' + num(t.ids.length) +
      " — остальные ищите поиском.</p>");
  }
  h.push("</section>");
  render(h.join(""));
}

/* --------------------------------------------------------------- поиск */
function viewSearch(q) {
  q = (q || "").trim();
  var h = [crumbs([{ t: "База знаний", href: "#/kb" }, { t: "Поиск" }])];
  h.push('<div class="kb-head"><h1>Поиск</h1>' +
    '<input class="kb-filter" id="kb-q" placeholder="Номер детали или наименование…" ' +
    'value="' + esc(q) + '"></div><div id="kb-res"></div>');
  render(h.join(""));
  var inp = document.getElementById("kb-q");
  inp.focus();
  inp.oninput = function () {
    var v = this.value;
    clearTimeout(inp._t);
    inp._t = setTimeout(function () {
      location.replace("#/search/" + encodeURIComponent(v));
      document.getElementById("kb-res").innerHTML = searchHtml(v);
    }, 180);
  };
  document.getElementById("kb-res").innerHTML = searchHtml(q);
}

function searchHtml(q) {
  q = (q || "").trim();
  if (q.length < 2) return '<p class="sub">Введите минимум два знака.</p>';
  var lo = q.toLowerCase(), key = norm(q);
  var h = [];

  var fl = FLEET.filter(function (m) {
    return (m.sn || "").toUpperCase().indexOf(q.toUpperCase()) >= 0 ||
      (m.name || "").toLowerCase().indexOf(lo) >= 0 ||
      (m.model || "").toLowerCase().indexOf(lo) >= 0 ||
      (m.garage || "") === q;
  }).slice(0, 20);
  if (fl.length) {
    h.push('<section class="kb-card wide"><h2>Парк машин <span class="cnt">' +
      fl.length + '</span></h2><table class="kb-table"><thead><tr>' +
      "<th>Предприятие</th><th>Машина</th><th>VIN</th><th>Гар. №</th>" +
      "<th>Год</th><th>Привязка</th></tr></thead><tbody>");
    fl.forEach(function (m) { h.push(fleetRow(m)); });
    h.push("</tbody></table></section>");
  }

  var hits = [];
  Object.keys(PARTS).forEach(function (no) {
    if (hits.length > 400) return;
    var p = PARTS[no];
    if ((key && norm(no).indexOf(key) !== -1) ||
        (p[0] && p[0].toLowerCase().indexOf(lo) !== -1) ||
        (p[1] && p[1].toLowerCase().indexOf(lo) !== -1) ||
        (p[2] && p[2].indexOf(q) !== -1)) hits.push(no);
  });
  hits.sort(function (a, b) {
    var ea = norm(a) === key ? 0 : 1, eb = norm(b) === key ? 0 : 1;
    return ea - eb || a.localeCompare(b);
  });
  if (hits.length) {
    h.push('<section class="kb-card wide"><h2>Детали <span class="cnt">' +
      hits.length + '</span></h2><table class="kb-table">');
    hits.slice(0, 200).forEach(function (no) {
      h.push("<tr><td class='c-id'>" + partLink(no) + "</td><td>" + esc(title(no)) +
        '<span class="sub"> ' + esc(subtitle(no)) + "</span></td>" +
        "<td class='c-eng'>" + marks(PARTS[no][4]) + "</td></tr>");
    });
    h.push("</table>" + (hits.length > 200
      ? '<p class="sub">Показаны первые 200.</p>' : "") + "</section>");
  }

  var ms = Object.keys(MACHINES).filter(function (c) {
    var m = MACHINES[c];
    return c.toLowerCase().indexOf(lo) >= 0 ||
      (m.model || "").toLowerCase().indexOf(lo) >= 0 ||
      (m.vin || "").toLowerCase().indexOf(lo) >= 0;
  });
  if (ms.length) {
    h.push('<section class="kb-card wide"><h2>Машины <span class="cnt">' +
      ms.length + '</span></h2><ul class="kb-list">' + ms.map(function (c) {
        return '<li><a href="#/machine/' + encodeURIComponent(c) + '">' +
          esc(MACHINES[c].model) + "</a><span class=\"sub\">" + esc(c) + "</span></li>";
      }).join("") + "</ul></section>");
  }

  if (!h.length) return '<p class="empty">Ничего не найдено.</p>';
  return h.join("");
}

/* -------------------------------------------------------------- маршрут */
function route() {
  var p = decodeURIComponent(location.hash.replace(/^#\/?/, "")).split("/");
  var parts = location.hash.replace(/^#\/?/, "").split("/").map(function (x) {
    try { return decodeURIComponent(x); } catch (e) { return x; }
  });
  var v = parts[0] || "kb";
  if (v === "kb" || v === "") viewHome();
  else if (v === "parts") viewParts(parts.slice(1).join("/"));
  else if (v === "part") viewPart(parts.slice(1).join("/"));
  else if (v === "machines") viewMachines();
  else if (v === "machine") viewMachine(parts[1]);
  else if (v === "section") viewSection(parts[1], parts.slice(2).join("/"));
  else if (v === "unit") viewUnit(parts[1], parts.slice(2).join("/"));
  else if (v === "fleet") viewFleet();
  else if (v === "topics") viewTopics();
  else if (v === "topic") viewTopic(parseInt(parts[1], 10));
  else if (v === "search") viewSearch(parts.slice(1).join("/"));
  else viewHome();
  void p;
}

/* Переход в каталог: из базы знаний туда ведут ссылки «открыть в
   каталоге». Каталог — отдельная страница, и состояние ему передаётся
   через localStorage: свой адрес он держит в history.state, а не в хеше. */
document.addEventListener("click", function (e) {
  var a = e.target.closest ? e.target.closest("a[data-catalog]") : null;
  if (!a) return;
  e.preventDefault();
  var v = a.getAttribute("data-catalog").split("|");
  try {
    localStorage.setItem("liugong_open", JSON.stringify(
      { book: v[0] || "", unit: v[1] || "", part: v[2] || "" }));
  } catch (err) { /* приватный режим */ }
  location.href = "index.html";
});

/* фотография во весь экран */
document.addEventListener("click", function (e) {
  var img = e.target;
  if (!img || img.tagName !== "IMG") return;
  if (!img.closest(".part-photos")) return;
  var ov = document.createElement("div");
  ov.className = "kb-lightbox";
  ov.innerHTML = '<img src="' + img.getAttribute("src") + '" alt="">';
  ov.onclick = function () { ov.remove(); };
  document.body.appendChild(ov);
});
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    var ov = document.querySelector(".kb-lightbox");
    if (ov) ov.remove();
  }
});

/* ------------------------------------------------------------- оболочка */
function setLang(v) {
  LANG = v === "en" ? "en" : v === "zh" ? "zh" : "ru";
  try { localStorage.setItem("liugong_lang", LANG); } catch (e) {}
  var box = document.getElementById("lang-switch");
  if (box) {
    Array.prototype.forEach.call(box.querySelectorAll("button"), function (b) {
      b.classList.toggle("on", b.getAttribute("data-lang") === LANG);
    });
  }
}

function wire() {
  setLang(LANG);
  var box = document.getElementById("lang-switch");
  Array.prototype.forEach.call(box.querySelectorAll("button"), function (b) {
    b.onclick = function () { setLang(b.getAttribute("data-lang")); route(); };
  });
  document.getElementById("theme-toggle").onclick = function () {
    var t = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem("liugong_theme", t); } catch (e) {}
  };
  var s = document.getElementById("search");
  s.oninput = function () {
    var v = this.value;
    clearTimeout(s._t);
    s._t = setTimeout(function () {
      if (v.trim().length >= 2) location.hash = "#/search/" + encodeURIComponent(v);
    }, 250);
  };
  document.getElementById("search-clear").onclick = function () {
    s.value = ""; location.hash = "#/kb";
  };
  window.addEventListener("hashchange", route);
}

wire();
route();
})();
