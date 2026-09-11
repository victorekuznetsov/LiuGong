/* Каталог запасных частей LiuGong — вся логика.

   Сделан по образцу каталога Komatsu АО «Полюс»: то же дерево разделов,
   тот же чертёж рядом с таблицей позиций, та же подгрузка по требованию —
   дерево при выборе книги, состав узла при его открытии, кусок поискового
   индекса при поиске. Данные лежат в `.js`, а не в `.json`, чтобы каталог
   открывался двойным щелчком по index.html без всякого сервера.

   Отличий от Komatsu три, и все они — от того, как устроен сам EPC LiuGong.

   Первое: книга здесь сделана не на диапазон заводских номеров, а на
   исполнение машины (materialNo), и выкачана по VIN конкретного борта.
   Поэтому машина парка привязана к книге либо точно (её VIN), либо «по
   модели» — и это видно в парке отдельной пометкой, а не замазано.

   Второе: у узла бывает несколько редакций чертежа со своими датами
   ввода. Выбрав борт, каталог подсказывает ту редакцию, которая
   действовала на дату выпуска машины.

   Третье: номера выносок на чертеже LiuGong нарисованы (у Komatsu на их
   месте пустые рамки). Поэтому выноски здесь — прозрачные области поверх
   нарисованных номеров, а не сами номера.
*/
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  };
  var norm = function (s) {
    return String(s == null ? "" : s).toUpperCase().replace(/[^0-9A-Z]/g, "");
  };
  function plural(n, one, few, many) {
    var a = Math.abs(n) % 100, b = a % 10;
    if (a > 10 && a < 20) return many;
    if (b > 1 && b < 5) return few;
    if (b === 1) return one;
    return many;
  }
  function num(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  var BOOKS = window.BOOKS || [];
  var FLEET = window.FLEET || [];
  var byCode = {};
  BOOKS.forEach(function (b) { byCode[b.code] = b; });

  var state = {
    view: "welcome",
    book: null,        // код открытой книги
    site: "",          // предприятие в шапке; пустое — все
    unit: null,        // открытый узел
    path: [],          // как сюда пришли по вложенным узлам
    machine: null,     // борт, по которому фильтруется применяемость
    highlight: null,   // позиция, ради которой сюда перешли
    part: null,        // номер, чья карточка открыта (вид "part")
    lang: "ru"         // язык наименований: zh | en | ru
  };
  try {
    state.lang = localStorage.getItem("liugong_lang") || "ru";
  } catch (e) { /* приватный режим */ }

  // ------------------------------------------------------------- загрузка --

  /* Данные книги — не JSON по fetch, а такие же файлы `.js`, как books.js и
     fleet.js: каждый присваивает свой кусок в window.__DATA__ и грузится
     обычным <script src>. Это не оптимизация, а необходимость — fetch()
     местного файла браузер молча блокирует, когда страница открыта прямо
     с диска (`file://…`, двойным щелчком по index.html, без сервера), и
     тогда во всех остальных отношениях рабочий каталог показывал бы пустое
     дерево с «Failed to fetch». Тег `<script>` этому ограничению не
     подчиняется — так же, как уже подчиняются ему сами books.js и
     fleet.js, — и один и тот же код одинаково работает и с диска, и через
     Vercel: там и тут просто соответственно бесплатное кеширование по
     Cache-Control из vercel.json тоже сохраняется, потому что имя файла
     не меняется между перезагрузками.

     Всё, что уже скачано, лежит в cache: одна и та же книга открывается
     по многу раз, а поиск ходит в одни и те же куски индекса. */
  window.__DATA__ = window.__DATA__ || {};
  var cache = {};

  function loadScript(key, url) {
    if (Object.prototype.hasOwnProperty.call(window.__DATA__, key)) {
      return Promise.resolve(window.__DATA__[key]);
    }
    if (cache[url]) return cache[url];
    cache[url] = new Promise(function (resolve, reject) {
      var el = document.createElement("script");
      el.src = url;
      el.onload = function () {
        if (Object.prototype.hasOwnProperty.call(window.__DATA__, key)) {
          resolve(window.__DATA__[key]);
        } else {
          reject(new Error(url + ": файл загрузился, но данных не оставил"));
        }
      };
      el.onerror = function () { reject(new Error(url + ": не найден")); };
      document.head.appendChild(el);
    });
    return cache[url];
  }

  function loadTree(code) {
    return loadScript("tree:" + code, "data/" + code + "/tree.js");
  }
  function loadUnit(code, id) {
    return loadScript("u:" + code + "/" + id, "data/" + code + "/u/" + id + ".js");
  }

  function loadShard(key) {
    var name = key.slice(0, 2) || "__";
    return loadScript("idx:" + name, "data/index/parts-" + name + ".js")
      .catch(function () { return {}; });
  }

  // ---------------------------------------------------------- перевод --

  /* В EPC LiuGong каталог ведётся на двух языках сразу: китайском и
     английском, и то и другое — заводское. В данные книги кладётся
     английское наименование, китайское и русское лежат отдельными
     таблицами и грузятся только тогда, когда язык переключили: тем, кто
     читает по-английски, лишние файлы ни к чему.

     Китайское — как в заводской книге. Русское собрано на сборке
     (tools/build_translate.py): где деталь есть в прайс-листе с русским
     наименованием, взято оттуда, остальное переведено по словарю
     техники. Чего в таблице нет, показывается по-английски: исходное
     честнее, чем угаданное. */
  var trTable = { zh: null, ru: null };

  function loadTranslate(lang) {
    if (lang === "en") return Promise.resolve({});
    if (trTable[lang]) return Promise.resolve(trTable[lang]);
    var file = lang === "zh" ? "data/names.js" : "data/ru.js";
    return loadScript(lang, file)
      .then(function (t) { trTable[lang] = t || {}; return trTable[lang]; })
      .catch(function () { trTable[lang] = {}; return trTable[lang]; });
  }

  /* Наименование на выбранном языке. Нет перевода — отдаём как в книге. */
  function tr(text) {
    if (!text || state.lang === "en") return text;
    var t = trTable[state.lang];
    return (t && t[text]) || text;
  }

  function busy(on) { document.body.classList.toggle("busy", !!on); }

  // ------------------------------------------------------------ снабжение --

  /* Цены и цепочки замен грузятся отдельно от самого каталога и по
     требованию: прайс-лист меняется на другом цикле, чем книга, и есть
     далеко не для всех номеров. Шарды нарезаны так же, как поисковый
     индекс, — по первым двум знакам номера, поэтому таблица одного узла
     обычно тянет один-два файла. */
  var supplyCache = {};   // точный номер детали -> запись снабжения

  function loadSupplyShard(key) {
    var name = key.slice(0, 2) || "__";
    return loadScript("sup:" + name, "data/supply/s-" + name + ".js")
      .catch(function () { return {}; });
  }

  /* Подгрузить снабжение для набора номеров и разложить в supplyCache.
     Возвращает promise, который разрешается, когда все нужные шарды легли
     в кэш — дальше данные читаются синхронно через supplyOf(). */
  function loadSupplyFor(parts) {
    var shards = {};
    parts.forEach(function (p) {
      if (p) shards[norm(p).slice(0, 2) || "__"] = 1;
    });
    return Promise.all(Object.keys(shards).map(loadSupplyShard)).then(function (list) {
      list.forEach(function (shard) {
        Object.keys(shard).forEach(function (k) { supplyCache[k] = shard[k]; });
      });
    });
  }

  function supplyOf(part) { return supplyCache[part] || null; }

  /* Цена в прайсе дана на два базиса поставки: (1) Магадан, Алдан,
     Хабаровск и (2) Лесосибирск, Таксимо, Новосибирск. Который из них
     нужен — зависит от предприятия, поэтому показываются оба, а не один
     «средний»: усреднять цены разных базисов нельзя. */
  var BASIS = {
    b1: "Магадан, Алдан, Хабаровск",
    b2: "Лесосибирск, Таксимо, Новосибирск"
  };

  function money(v) {
    return num(Math.round(v)) + " ₽";
  }

  function priceCell(part, basis) {
    var s = supplyOf(part);
    var p = s && s.p;
    if (!p || p[basis] == null) return '<span class="stock-none">—</span>';
    var other = basis === "b1" ? "b2" : "b1";
    var title = "Базис " + BASIS[basis] + "\n" + money(p[basis]) + " без НДС" +
      (p[other] != null ? "\n\nБазис " + BASIS[other] + ": " + money(p[other]) : "") +
      (p.n ? "\n\n" + p.n : "");
    return '<span class="price" title="' + esc(title) + '">' + money(p[basis]) + "</span>";
  }

  /* Пометка о замене. В выгрузке EPC отдельного поля с цепочкой замен нет:
     замена записана словами в примечании к позиции, и сборщик
     (tools/build_supply.py) вынимает её оттуда, принимая только те
     номера, которые есть в самом каталоге. */
  function chainOf(part) {
    var s = supplyOf(part);
    return (s && s.c) || [];
  }

  function flagsOf(part) {
    var s = supplyOf(part);
    return (s && s.f) || [];
  }

  function codeText(code) {
    var c = (window.CODES || {})[code] || {};
    return { tag: c.s || code, full: c.f || c.s || code };
  }

  function chainCell(part) {
    var c = chainOf(part), f = flagsOf(part);
    if (!c.length && !f.length) return '<span class="stock-none">—</span>';
    var out = "";
    f.forEach(function (code) {
      var t = codeText(code);
      out += '<span class="flag-pill flag-' + esc(code) + '" title="' + esc(t.full) +
        '">' + esc(t.tag) + "</span>";
    });
    c.slice(0, 2).forEach(function (l) {
      var t = codeText(l.code);
      var no = l.d || l.n;
      /* Номер, которого нет ни в одной книге каталога, ссылкой не делаем:
         открывать нечего. Но и молчать о нём нельзя — завод заменил
         деталь именно на него. */
      out += l.x
        ? '<span class="chain-pill chain-out" title="' +
          esc(t.full + "\n\nЭтого номера нет ни в одной книге каталога.") + '">' +
          esc(t.tag) + " " + esc(no) + "</span>"
        : '<span class="chain-pill pn-link" data-part="' + esc(no) +
          '" title="' + esc(t.full) + '">' + esc(t.tag) + " " + esc(no) + "</span>";
    });
    if (c.length > 2) out += '<span class="chain-more">ещё ' + (c.length - 2) + "</span>";
    return out;
  }

  /* Рекомендация EPC по складскому запасу приходит по-английски и всего
     семью значениями. Переводятся они на показе, а в данных остаются как
     их написал завод. */
  var STORE_RU = {
    "not recommend": "не рекомендуется", "1 year": "1 год", "2 years": "2 года",
    "3 years": "3 года", "5 years": "5 лет", "1000h": "1000 ч", "500h": "500 ч"
  };

  function storeRu(v) {
    return STORE_RU[String(v || "").trim().toLowerCase()] || v;
  }

  function storeCell(row) {
    var v = row[5] || "";
    if (!v) return '<span class="stock-none">—</span>';
    return '<span class="store-pill" title="' +
      esc("Рекомендация EPC по складскому запасу: " + v) + '">' +
      esc(storeRu(v)) + "</span>";
  }

  /* Патч уже нарисованной таблицы после того, как подъехали цены и замены —
     без этого пришлось бы ждать сеть перед первой отрисовкой узла. */
  function refreshSupplyCells(body) {
    Array.prototype.forEach.call(body.querySelectorAll("tr[data-no]"), function (tr) {
      var part = tr.getAttribute("data-no");
      if (!part) return;
      var ch = tr.querySelector(".c-chain");
      if (ch) ch.innerHTML = chainCell(part);
      var p1 = tr.querySelector(".c-p1");
      if (p1) p1.innerHTML = priceCell(part, "b1");
      var p2 = tr.querySelector(".c-p2");
      if (p2) p2.innerHTML = priceCell(part, "b2");
    });
    Array.prototype.forEach.call(body.querySelectorAll(".c-chain .pn-link"), function (el) {
      el.onclick = function (e) {
        e.stopPropagation();
        openPart(el.getAttribute("data-part"));
      };
    });
  }

  // --------------------------------------------------- применяемость --

  /* Признаки строки лежат одним числом: девять почти всегда пустых полей
     в шестидесяти тысячах строк весили бы больше самих данных.
     Разрядность та же, что в tools/build_catalog.py. */
  var F_KIT = 1, F_REMAN = 2, F_PHOTO = 4, F_SUPERS = 8, F_BULLETIN = 16,
      F_FIT = 32, F_NOORDER = 64;

  function flag(row, bit) { return ((row[7] || 0) & bit) !== 0; }

  /* Диапазонов заводских номеров, как у Komatsu, в EPC LiuGong нет: книга
     сделана на исполнение машины, а не на серию. Зато у каждой позиции
     есть заводская отметка «входит в исполнение, по которому книга
     выкачана» — её EPC и ставит в своём дереве. Это и есть здешняя
     применяемость, и называется она в интерфейсе своим именем, а не
     «серийными номерами»: у машины той же модели, но другого исполнения,
     отметка может значить не то же самое. */
  function appliesTo(row, machine) {
    if (!machine) return true;
    return flag(row, F_FIT);
  }

  /* Дата выпуска машины числом `ггггммдд` — из года выпуска и плановой
     даты ввода в эксплуатацию. Нужна, чтобы сказать, какая редакция
     чертежа действовала, когда машина вышла с завода. */
  function machineDate(m) {
    if (!m) return "";
    var d = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(m.start || "");
    if (d) return d[3] + d[2] + d[1];
    if (/^\d{4}$/.test(m.year || "")) return m.year + "1231";
    return "";
  }

  function dateNum(iso) {
    var d = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    return d ? d[1] + d[2] + d[3] : "";
  }

  /* Редакция чертежа, действовавшая на дату выпуска борта: самая поздняя
     из тех, что введены не позже этой даты. Если все редакции новее
     машины — ничего не выбираем: подсказка «эта» была бы неправдой. */
  function revisionFor(node, machine) {
    var when = machineDate(machine);
    if (!when || !node) return null;
    var all = [node].concat(node.kids || []).filter(function (n) {
      return n.g && n.ref === node.ref && n.d;
    });
    var fit = all.filter(function (n) { return dateNum(n.d) <= when; });
    if (!fit.length) return null;
    fit.sort(function (a, b) { return dateNum(b.d).localeCompare(dateNum(a.d)); });
    return fit[0];
  }

  // ------------------------------------------------------------------ парк --

  function machinesOf(code) {
    return FLEET.filter(function (m) { return m.books.indexOf(code) >= 0; });
  }

  function sites() {
    var seen = {}, out = [];
    FLEET.forEach(function (m) {
      if (m.be && !seen[m.be]) { seen[m.be] = 1; out.push(m.be); }
    });
    return out.sort();
  }

  function booksOfSite(site) {
    if (!site) return BOOKS.slice();
    var seen = {};
    FLEET.forEach(function (m) {
      if (m.be === site) m.books.forEach(function (c) { seen[c] = 1; });
    });
    return BOOKS.filter(function (b) { return seen[b.code]; });
  }

  // ----------------------------------------------------------------- шапка --

  function fillHeader() {
    var ss = $("site-select");
    ss.innerHTML = '<option value="">Все предприятия</option>' +
      sites().map(function (s) {
        return '<option value="' + esc(s) + '">' + esc(s) + "</option>";
      }).join("");
    ss.value = state.site;
    ss.onchange = function () {
      state.site = ss.value;
      var list = booksOfSite(state.site);
      fillBooks();
      if (list.length && !list.some(function (b) { return b.code === state.book; })) {
        selectBook(list[0].code);
      } else {
        renderPassport();
      }
    };
    fillBooks();
  }

  function fillBooks() {
    var list = booksOfSite(state.site), bs = $("book-select");
    bs.innerHTML = list.map(function (b) {
      var n = machinesOf(b.code).filter(function (m) {
        return !state.site || m.be === state.site;
      }).length;
      return '<option value="' + esc(b.code) + '">' +
        esc(b.model + (b.kind ? " · " + b.kind : "")) +
        (n ? "  — " + n + " " + plural(n, "машина", "машины", "машин") : "") +
        "</option>";
    }).join("");
    bs.value = state.book;
    bs.onchange = function () { selectBook(bs.value); };
  }

  function renderPassport() {
    var b = byCode[state.book];
    if (!b) { $("passport").innerHTML = ""; return; }
    var mm = machinesOf(b.code).filter(function (m) {
      return !state.site || m.be === state.site;
    });
    var cells = [
      ["Модель", b.model],
      ["Вид техники", b.kind || "—"],
      ["Исполнение", b.code],
      ["VIN выгрузки", b.vin || "—"],
      ["Узлов", num(b.units)],
      ["Позиций", num(b.lines)],
      ["Номеров", num(b.numbers)],
      ["Машин в парке", String(mm.length)]
    ];
    $("passport").innerHTML = cells.map(function (c) {
      return '<div class="pp"><span class="pp-k">' + esc(c[0]) +
        '</span><span class="pp-v">' + esc(c[1]) + "</span></div>";
    }).join("");
  }

  // ---------------------------------------------------------------- дерево --

  var tree = null;          // дерево открытой книги
  var unitsFlat = [];       // все узлы книги подряд, для фильтра и поиска
  var refIndex = {};        // заводской номер сборки → узел

  function flatten(nodes, out, depth) {
    nodes.forEach(function (n) {
      n.depth = depth;
      out.push(n);
      if (n.ref) refIndex[norm(n.ref)] = n;
      if (n.kids) flatten(n.kids, out, depth + 1);
    });
    return out;
  }

  /* `machine` — если книгу открывают вместе с выбором борта (щелчок по
     машине на стартовой странице или в парке), передаётся сюда, а не
     ставится в state отдельно: иначе сброс state.machine=null двумя
     строками ниже тут же стирал бы то, что только что выбрали. */
  function selectBook(code, then, machine) {
    if (!byCode[code]) return;
    state.book = code;
    state.unit = null;
    state.path = [];
    state.machine = machine || null;
    busy(true);
    var ready = loadTranslate(state.lang);
    ready.then(function () { return loadTree(code); }).then(function (t) {
      tree = t;
      refIndex = {};
      unitsFlat = flatten(t, [], 0);
      $("book-select").value = code;
      renderPassport();
      renderTree($("tree-search").value);
      openWelcome();
      busy(false);
      if (then) then();
    }).catch(function (e) {
      busy(false);
      $("tree").innerHTML = '<div class="tree-note">Не удалось загрузить книгу: ' +
        esc(e.message) + "</div>";
    });
  }

  function renderTree(filter) {
    if (!tree) return;
    var qt = (filter || "").trim().toLowerCase(), q = norm(filter || "");
    var html = tree.map(function (sec) {
      var kids = (sec.kids || []).filter(function (u) {
        if (!qt) return true;
        return (u.title || "").toLowerCase().indexOf(qt) >= 0 ||
          (tr(u.title) || "").toLowerCase().indexOf(qt) >= 0 ||
          (u.ref && norm(u.ref).indexOf(q) >= 0);
      });
      if (qt && !kids.length && (sec.title || "").toLowerCase().indexOf(qt) < 0 &&
          (tr(sec.title) || "").toLowerCase().indexOf(qt) < 0) return "";
      if (qt && !kids.length) kids = sec.kids || [];
      var open = !!qt || kids.some(function (u) { return inBranch(u, state.unit); });
      return '<div class="tree-sys' + (open ? " open" : "") + '">' +
        '<div class="tree-sys-head"><span>' + esc(tr(sec.title) || sec.id) + "</span>" +
        '<span class="cnt">' + kids.length + "</span></div>" +
        '<div class="tree-opts">' + kids.map(nodeHtml).join("") + "</div></div>";
    }).join("");
    var t = $("tree");
    t.innerHTML = html || '<div class="tree-note">Ничего не найдено</div>';
    Array.prototype.forEach.call(t.querySelectorAll(".tree-sys-head"), function (h) {
      h.onclick = function () { h.parentNode.classList.toggle("open"); };
    });
    Array.prototype.forEach.call(t.querySelectorAll(".tree-opt[data-unit]"), function (o) {
      o.onclick = function (e) {
        e.stopPropagation();
        openUnit(o.getAttribute("data-unit"));
      };
    });
  }

  /* Узел без чертежа (`n`) — просто заголовок группы: в EPC такие узлы
     есть, но состава у них нет, и открывать там нечего. Кликабельным его
     делать нельзя: щелчок кончился бы ошибкой загрузки. */
  function nodeHtml(u) {
    var kids = u.kids || [];
    var open = !u.n;
    return '<div class="tree-opt' + (u.id === state.unit ? " active" : "") +
      (kids.length ? " has-kids" : "") + (open ? "" : " tree-group") + '"' +
      (open ? ' data-unit="' + esc(u.id) + '"' : "") + ">" +
      esc(tr(u.title) || u.id) +
      '<span class="no">' + (u.ref ? esc(u.ref) : esc(u.id)) +
      (u.d ? " · " + esc(u.d) : "") +
      (kids.length ? " · " + kids.length + " " +
        plural(kids.length, "чертёж", "чертежа", "чертежей") : "") +
      "</span></div>" +
      (kids.length ? '<div class="tree-sub">' + kids.map(nodeHtml).join("") + "</div>" : "");
  }

  function inBranch(node, id) {
    if (!id) return false;
    if (node.id === id) return true;
    return (node.kids || []).some(function (k) { return inBranch(k, id); });
  }

  function findNode(id, nodes) {
    nodes = nodes || tree || [];
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].id === id) return nodes[i];
      var f = findNode(id, nodes[i].kids || []);
      if (f) return f;
    }
    return null;
  }

  // ------------------------------------------------------------------ виды --

  var VIEWS = ["welcome", "unit", "search", "part", "fleet", "check"];

  /* Кнопка «← Назад» — это history.back(), поэтому у каждого вида должна
     быть запись в истории браузера; без неё «назад» уходит со страницы
     каталога вовсе (на предыдущий сайт или на пустую вкладку), а не на
     предыдущий экран каталога. `restoring` не даёт продублировать запись,
     пока мы сами восстанавливаем состояние по popstate. */
  var restoring = false;

  function snapshot() {
    return {
      view: state.view, book: state.book, site: state.site,
      unit: state.unit, path: (state.path || []).slice(),
      mi: state.machine ? FLEET.indexOf(state.machine) : -1,
      highlight: state.highlight, part: state.part,
      applic: applicFilter, fleetFilter: fleetFilter,
      search: $("search") ? $("search").value : ""
    };
  }

  function show(v) {
    state.view = v;
    VIEWS.forEach(function (name) {
      $("view-" + name).classList.toggle("hidden", name !== v);
    });
    $("navbar").classList.toggle("hidden", v === "welcome");
    window.scrollTo(0, 0);
    if (!restoring) history.pushState(snapshot(), "");
  }

  function restoreView(st) {
    if (!st) { openWelcome(); return; }
    restoring = true;
    state.site = st.site || "";
    applicFilter = !!st.applic;
    fleetFilter = st.fleetFilter || "";
    if ($("search")) $("search").value = st.search || "";
    var machine = st.mi >= 0 ? FLEET[st.mi] : null;
    var after = function () {
      state.machine = machine;
      if (st.view === "unit" && st.unit) openUnit(st.unit, st.path, st.highlight);
      else if (st.view === "search" && st.search) runSearch(st.search);
      else if (st.view === "fleet") openFleet();
      else if (st.view === "check") show("check");
      else if (st.view === "part" && st.part) openPart(st.part);
      else openWelcome();
      restoring = false;
    };
    if (st.book && st.book !== state.book) selectBook(st.book, after, machine);
    else after();
  }

  window.addEventListener("popstate", function (e) { restoreView(e.state); });

  function openWelcome() {
    var b = byCode[state.book];
    if (!b) return;
    $("w-title").textContent = "Каталог запасных частей LiuGong " + b.model;
    $("w-lead").textContent = (b.kind ? b.kind + " · " : "") +
      "исполнение " + b.code + (b.vin ? " · выкачан по VIN " + b.vin : "");
    var stats = [
      [num(b.units), plural(b.units, "узел", "узла", "узлов")],
      [num(b.sheets), plural(b.sheets, "чертёж", "чертежа", "чертежей")],
      [num(b.lines), plural(b.lines, "позиция", "позиции", "позиций")],
      [num(b.numbers), plural(b.numbers, "номер детали", "номера деталей", "номеров деталей")],
      [num(b.spots), "выносок на чертежах"]
    ];
    $("w-stats").innerHTML = stats.map(function (s) {
      return '<div class="stat"><b>' + esc(s[0]) + "</b><span>" + esc(s[1]) + "</span></div>";
    }).join("");

    var mm = machinesOf(b.code).filter(function (m) {
      return !state.site || m.be === state.site;
    });
    $("w-mach-lead").textContent = mm.length
      ? "Щелчок по машине выбирает борт: в таблице позиций можно оставить "
        + "только входящее в её исполнение, а у узлов с несколькими "
        + "редакциями чертежа каталог подскажет ту, что действовала на дату выпуска."
      : "В выгрузке парка машин под этот каталог не нашлось.";
    $("w-machines").innerHTML = mm.map(function (m, i) {
      return '<div class="doc-item" data-mach="' + i + '">' +
        '<span class="doc-kind">' + esc(m.model) + "</span>" +
        '<span class="doc-name">' + esc(m.name || m.model) +
        '<span class="doc-note">' + esc(m.be) + " · " + esc(m.mvz) + "</span></span>" +
        '<span class="doc-meta">VIN ' + esc(m.sn || "—") +
        (m.garage ? " · гар. " + esc(m.garage) : "") +
        (m.fit === "vin" ? " · каталог по этому VIN"
                         : " · каталог по VIN другой машины той же модели") +
        "</span></div>";
    }).join("");
    Array.prototype.forEach.call($("w-machines").querySelectorAll("[data-mach]"), function (el) {
      el.onclick = function () {
        state.machine = mm[parseInt(el.getAttribute("data-mach"), 10)];
        openWelcome();
        if (state.unit) openUnit(state.unit);
      };
    });
    show("welcome");
  }

  // -------------------------------------------------------------- узел (вид) --

  var curUnit = null;

  function openUnit(id, path, highlight) {
    var node = findNode(id);
    if (!node) return;
    state.unit = id;
    state.path = path || [];
    state.highlight = highlight || null;
    busy(true);
    loadUnit(state.book, id).then(function (page) {
      curUnit = page;
      renderUnit(node, page);
      renderTree($("tree-search").value);
      busy(false);
      show("unit");
    }).catch(function (e) {
      busy(false);
      alert("Не удалось открыть узел " + id + ": " + e.message);
    });
  }

  function renderUnit(node, page) {
    var b = byCode[state.book];
    var crumbs = ['<span class="crumb" data-go="welcome">' + esc(b.model) + "</span>"];
    state.path.forEach(function (pid, i) {
      var pn = findNode(pid);
      if (pn) crumbs.push('<span class="crumb" data-back="' + i + '">' +
        esc(tr(pn.title) || pid) + "</span>");
    });
    crumbs.push('<span class="crumb cur">' + esc(tr(page.t || node.title)) + "</span>");
    $("opt-crumbs").innerHTML = crumbs.join('<span class="crumb-sep">›</span>');
    var go = $("opt-crumbs").querySelector("[data-go]");
    if (go) go.onclick = openWelcome;
    Array.prototype.forEach.call($("opt-crumbs").querySelectorAll("[data-back]"), function (el) {
      el.onclick = function () {
        var i = parseInt(el.getAttribute("data-back"), 10);
        openUnit(state.path[i], state.path.slice(0, i));
      };
    });

    $("opt-name").textContent = tr(page.t || node.title) || page.id;
    var shown = visibleRows(page);
    $("opt-meta").textContent =
      (page.r ? "Номер сборки " + page.r + " · " : "") +
      page.id + " · " + shown.length + " " +
      plural(shown.length, "позиция", "позиции", "позиций") +
      (shown.length !== page.rows.length
        ? " из " + page.rows.length + " (фильтр по борту)" : "") +
      (page.d ? " · редакция от " + page.d : "");

    renderApplicBar(page);
    renderDrawing(page);
    renderParts(page, shown);
  }

  /* Строки, которые видны при выбранном борте. Фильтр включается только
     когда борт выбран: без него книга показывается целиком, как есть. */
  function visibleRows(page) {
    if (!state.machine || !filterOn()) return page.rows;
    return page.rows.filter(function (r) { return appliesTo(r, state.machine); });
  }

  var applicFilter = false;
  function filterOn() { return applicFilter; }

  function renderApplicBar(page) {
    var bar = $("applic-bar");
    if (!state.machine) {
      bar.innerHTML = '<span class="applic-note">Борт не выбран — каталог показан целиком. ' +
        'Выбрать борт можно на стартовой странице книги или в «Парке».</span>';
      return;
    }
    var m = state.machine;
    var hidden = page.rows.length - visibleRows(page).length;
    var exact = m.fit === "vin";
    var node = findNode(state.unit);
    var rev = revisionFor(node, m);
    var revNote = "";
    if (rev && rev.id !== page.id) {
      revNote = '<button class="btn-plain applic-rev" data-rev="' + esc(rev.id) +
        '" title="' + esc("На дату выпуска машины действовала редакция от " + rev.d) +
        '">открыть редакцию от ' + esc(rev.d) + "</button>";
    } else if (rev && page.d) {
      revNote = '<span class="applic-ok" title="' +
        esc("Эта редакция чертежа введена " + page.d +
            " и действовала на дату выпуска машины") + '">редакция по дате выпуска</span>';
    }
    bar.innerHTML =
      '<label class="applic-toggle"><input type="checkbox" id="applic-cb"' +
      (applicFilter ? " checked" : "") + "> Только входящее в исполнение</label>" +
      '<span class="applic-note">' + esc(m.model) +
      (m.garage ? " №" + esc(m.garage) : "") + " · VIN " + esc(m.sn || "—") +
      (exact ? " · каталог выкачан по этому VIN"
             : " · каталог той же модели, но по VIN другой машины: исполнения совпадают не всегда") +
      (applicFilter && hidden > 0 ? " · скрыто " + hidden + " " +
        plural(hidden, "позиция", "позиции", "позиций") : "") +
      "</span>" + revNote +
      '<button class="btn-plain" id="applic-off">сбросить борт</button>';
    var cb = $("applic-cb");
    if (cb) cb.onchange = function () { applicFilter = cb.checked; openUnit(state.unit, state.path); };
    var off = $("applic-off");
    if (off) off.onclick = function () {
      state.machine = null; applicFilter = false; openUnit(state.unit, state.path);
    };
    var go = bar.querySelector("[data-rev]");
    if (go) go.onclick = function () { openUnit(go.getAttribute("data-rev"), state.path); };
  }

  function renderDrawing(page) {
    var img = $("drawing"), pane = $("drawing-pane");
    if (!page.g && !hasDrawing(page)) {
      pane.classList.add("hidden");
      return;
    }
    pane.classList.remove("hidden");
    /* Чертежи LiuGong все векторные: EPC отдаёт SVG, а не скан. */
    img.src = "media/" + state.book + "/" + page.id + ".svg";
    img.alt = page.t || page.id;
    $("drawing-hint").textContent = "Чертёж " + (page.g || page.id) +
      (page.d ? " · редакция от " + page.d : "") +
      " · щелчок по номеру на чертеже — найти позицию в таблице · " +
      "щелчок по чертежу — увеличить";
    img.onclick = function () {
      $("lightbox-img").src = img.src;
      /* Увеличенный чертёж — та же картинка, и области выносок на ней
         нужны ровно так же. */
      paintSpots(page, $("lightbox-spots"), true);
      fitLightbox(page);
      $("lightbox").classList.remove("hidden");
    };
    img.onload = function () { renderSpots(page); };
    if (img.complete) renderSpots(page);
  }

  function hasDrawing(page) { return page.spots && page.spots.length; }

  /* Коробка увеличенного чертежа считается в пикселях, а не отдаётся
     браузеру: у чертежа-вектора нет собственного размера — только
     viewBox, — и «вписать по высоте» такую картинку сама разметка не
     умеет, коробка схлопывается в ноль вместе с выносками. */
  var lbPage = null;

  function fitLightbox(page) {
    lbPage = page;
    var pad = 48;
    var ar = page.w / page.h;
    var w = Math.min(window.innerWidth - pad, (window.innerHeight - pad) * ar);
    var wrap = $("lightbox-wrap");
    wrap.style.width = Math.max(1, Math.round(w)) + "px";
    wrap.style.height = Math.max(1, Math.round(w / ar)) + "px";
  }

  window.addEventListener("resize", function () {
    if (lbPage && !$("lightbox").classList.contains("hidden")) fitLightbox(lbPage);
  });

  /* Номера выносок на чертеже LiuGong нарисованы — в отличие от книги
     Komatsu, где на их месте пустые рамки. Поэтому поверх картинки
     кладутся прозрачные области ровно по нарисованным номерам: рисовать
     номер поверх номера незачем, а кликабельность в обе стороны нужна
     такая же. Координаты областей сняты со самого чертежа на сборке. */
  function renderSpots(page) { paintSpots(page, $("spots"), false); }

  function paintSpots(page, box, inLightbox) {
    if (!page.spots || !page.spots.length || !page.w || !page.h) {
      box.innerHTML = ""; return;
    }
    var shown = {};
    visibleRows(page).forEach(function (r) { shown[r[0]] = 1; });
    box.innerHTML = page.spots.map(function (s) {
      var item = s[0], x1 = s[1], y1 = s[2], x2 = s[3], y2 = s[4];
      var l = 100 * x1 / page.w, t = 100 * y1 / page.h;
      var w = 100 * (x2 - x1) / page.w, h = 100 * (y2 - y1) / page.h;
      return '<span class="spot' + (shown[item] ? "" : " spot-off") +
        '" data-item="' + esc(item) + '" style="left:' + l.toFixed(3) + "%;top:" +
        t.toFixed(3) + "%;width:" + w.toFixed(3) + "%;height:" + h.toFixed(3) +
        '%">' + esc(item) + "</span>";
    }).join("");
    Array.prototype.forEach.call(box.querySelectorAll(".spot"), function (el) {
      el.onclick = function (e) {
        e.stopPropagation();
        if (inLightbox) $("lightbox").classList.add("hidden");
        markItem(el.getAttribute("data-item"), true);
      };
    });
  }

  function markItem(item, scroll) {
    Array.prototype.forEach.call(document.querySelectorAll(".spots .spot"), function (el) {
      el.classList.toggle("hit", el.getAttribute("data-item") === item);
    });
    var row = null;
    Array.prototype.forEach.call($("parts-body").querySelectorAll("tr"), function (tr) {
      var on = tr.getAttribute("data-item") === item;
      tr.classList.toggle("hit-row", on);
      if (on && !row) row = tr;
    });
    if (row && scroll) row.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  function renderParts(page, rows) {
    var body = $("parts-body");
    body.innerHTML = rows.map(function (r) {
      var item = r[0] || "", part = r[1] || "", name = r[2] || "";
      var qty = r[3] == null ? "" : r[3], note = r[4] || "", link = r[6] || "";
      var sub = link && refIndex[norm(link)];
      var hit = state.highlight && norm(part) === norm(state.highlight);
      var marks = "";
      if (flag(r, F_KIT)) marks += '<span class="mark kit" title="Ремкомплект">К</span>';
      if (flag(r, F_REMAN)) marks += '<span class="mark reman" title="Поставляется восстановленной">R</span>';
      if (flag(r, F_NOORDER)) marks += '<span class="mark noorder" title="Отдельно не поставляется">✕</span>';
      var mpq = r[8] || "";
      var cls = (hit ? " hit-row" : "") +
        (state.machine && !flag(r, F_FIT) ? " row-other" : "");
      return "<tr" + (cls ? ' class="' + cls.slice(1) + '"' : "") +
        ' data-item="' + esc(item) + '" data-no="' + esc(part) + '">' +
        '<td class="c-pos">' + esc(item) + "</td>" +
        '<td class="c-no">' + (part
          ? '<span class="pn pn-link" data-part="' + esc(part) + '">' + esc(part) + "</span>" +
            (mpq ? '<span class="mpq" title="' +
              esc("Минимальная партия поставки — " + mpq + " шт.") + '">×' + esc(mpq) + "</span>" : "")
          : "") + "</td>" +
        '<td class="c-name">' +
          (sub ? '<span class="go-sub" data-sub="' + esc(sub.id) +
            '" title="Открыть вложенный узел">▸</span>' : "") +
          esc(tr(name)) + marks + "</td>" +
        '<td class="c-qty">' + esc(qty) + "</td>" +
        '<td class="c-note">' + (note
          ? '<span class="note-cell" title="' + esc(note) + '">' + esc(note) + "</span>"
          : '<span class="stock-none">—</span>') + "</td>" +
        '<td class="c-store">' + storeCell(r) + "</td>" +
        '<td class="c-chain">' + (part ? chainCell(part) : "") + "</td>" +
        '<td class="c-p1">' + (part ? priceCell(part, "b1") : "") + "</td>" +
        '<td class="c-p2">' + (part ? priceCell(part, "b2") : "") + "</td>" +
        '<td class="c-need"><input class="need-input" type="number" min="1" value="' +
          (parseInt(qty, 10) > 0 ? parseInt(qty, 10) : 1) + '"></td>' +
        '<td class="c-add">' + (part ? '<button class="btn-add">＋ в заказ</button>' : "") +
        "</td></tr>";
    }).join("");

    /* Цены и цепочки замен — данные не самого каталога, а прайс-листа и
       примечаний: грузятся отдельно и патчатся в уже нарисованную
       таблицу, как только нужные шарды подъедут. */
    var partsOnPage = rows.map(function (r) { return r[1]; }).filter(Boolean);
    if (partsOnPage.length) {
      loadSupplyFor(partsOnPage).then(function () { refreshSupplyCells(body); });
    }

    Array.prototype.forEach.call(body.querySelectorAll("tr"), function (tr) {
      tr.onclick = function (e) {
        if (e.target.closest("button, input, .pn-link, .go-sub")) return;
        markItem(tr.getAttribute("data-item"), false);
      };
    });
    Array.prototype.forEach.call(body.querySelectorAll(".go-sub"), function (el) {
      el.onclick = function () {
        openUnit(el.getAttribute("data-sub"), state.path.concat([state.unit]));
      };
    });
    Array.prototype.forEach.call(body.querySelectorAll(".pn-link"), function (el) {
      el.onclick = function () { openPart(el.getAttribute("data-part")); };
    });
    Array.prototype.forEach.call(body.querySelectorAll(".btn-add"), function (btn) {
      btn.onclick = function () {
        var tr = btn.closest("tr");
        addToCart(tr.getAttribute("data-no"),
          tr.querySelector(".c-name").textContent.replace(/^▸/, "").trim(),
          parseInt(tr.querySelector(".need-input").value, 10) || 1);
        btn.classList.add("done");
        btn.textContent = "✓ в заказе";
      };
    });
    var hit = body.querySelector("tr.hit-row");
    if (hit) setTimeout(function () {
      hit.scrollIntoView({ block: "center", behavior: "smooth" });
      markItem(hit.getAttribute("data-item"), false);
    }, 60);
  }

  // ---------------------------------------------------------------- поиск --

  var searchTimer = null;

  function runSearch(q) {
    q = (q || "").trim();
    if (q.length < 2) { openWelcome(); return; }
    busy(true);
    var key = norm(q);
    var byNumber = key.length >= 3;
    (byNumber ? loadShard(key) : Promise.resolve({})).then(function (shard) {
      var hits = [];
      Object.keys(shard).forEach(function (k) {
        if (k.indexOf(key) !== 0) return;
        shard[k].forEach(function (h) {
          hits.push({ code: h[0], page: h[1], item: h[2], part: h[3], exact: k === key });
        });
      });
      renderSearch(q, hits, byNumber);
      busy(false);
    }).catch(function () { busy(false); });
  }

  function renderSearch(q, hits, byNumber) {
    hits.sort(function (a, b) {
      return (b.exact - a.exact) || a.code.localeCompare(b.code) ||
        a.page.localeCompare(b.page);
    });
    $("search-title").textContent = "Поиск: " + q;
    if (!hits.length) {
      $("search-results").innerHTML = '<p class="sub">' + (byNumber
        ? "Такого номера нет ни в одной книге каталога."
        : "Для поиска по номеру наберите хотя бы три знака.") + "</p>";
      show("search");
      return;
    }
    var groups = {};
    hits.forEach(function (h) { (groups[h.part] = groups[h.part] || []).push(h); });
    var html = Object.keys(groups).sort().map(function (part) {
      var list = groups[part];
      return '<div class="find-group"><div class="find-no">' +
        '<span class="pn pn-link" data-part="' + esc(part) + '">' + esc(part) + "</span>" +
        '<span class="sub"> — ' + list.length + " " +
        plural(list.length, "применение", "применения", "применений") + "</span></div>" +
        list.map(function (h) {
          var b = byCode[h.code];
          return '<div class="find-hit" data-code="' + esc(h.code) + '" data-page="' +
            esc(h.page) + '" data-part="' + esc(part) + '">' +
            '<span class="fh-book">' + esc(b ? b.model : h.code) + "</span>" +
            '<span class="fh-unit">' + esc(h.page) + "</span>" +
            '<span class="fh-item">поз. ' + esc(h.item) + "</span></div>";
        }).join("") + "</div>";
    }).join("");
    $("search-results").innerHTML = html;
    bindHits($("search-results"));
    show("search");
  }

  function bindHits(root) {
    Array.prototype.forEach.call(root.querySelectorAll(".find-hit"), function (el) {
      el.onclick = function () {
        var code = el.getAttribute("data-code");
        var page = el.getAttribute("data-page");
        var part = el.getAttribute("data-part");
        if (code === state.book) openUnit(page, [], part);
        else selectBook(code, function () { openUnit(page, [], part); });
      };
    });
    Array.prototype.forEach.call(root.querySelectorAll(".pn-link"), function (el) {
      el.onclick = function () { openPart(el.getAttribute("data-part")); };
    });
  }

  // ------------------------------------------------------- карточка детали --

  function openPart(part) {
    state.part = part;
    busy(true);
    var key = norm(part);
    Promise.all([loadShard(key), loadSupplyFor([part]), loadInfoFor(part)]).then(function (res) {
      var shard = res[0];
      var hits = (shard[key] || []).map(function (h) {
        return { code: h[0], page: h[1], item: h[2], part: h[3] };
      });
      var books = {};
      hits.forEach(function (h) { books[h.code] = (books[h.code] || 0) + 1; });
      var kb = partInfo(part) || {};
      var name = kb.ru || kb.en || "";
      $("part-card").innerHTML =
        '<div class="pc-head"><button class="btn-plain pc-close" id="pc-close" ' +
        'title="Закрыть карточку">✕</button>' +
        '<h2 class="view-title">' + esc(part) + "</h2>" +
        '<div class="sub">' + hits.length + " " +
        plural(hits.length, "применение", "применения", "применений") + " в " +
        Object.keys(books).length + " " +
        plural(Object.keys(books).length, "каталоге", "каталогах", "каталогах") + "</div></div>" +
        '<div class="pc-body"><div class="pc-info">' +
        supplyBlocks(part) +
        '<h3>Где применяется</h3>' +
        hits.map(function (h) {
          var b = byCode[h.code];
          return '<div class="find-hit" data-code="' + esc(h.code) + '" data-page="' +
            esc(h.page) + '" data-part="' + esc(part) + '">' +
            '<span class="fh-book">' + esc(b ? b.model + " · " + b.code : h.code) + "</span>" +
            '<span class="fh-unit">' + esc(h.page) + "</span>" +
            '<span class="fh-item">поз. ' + esc(h.item) + "</span></div>";
        }).join("") +
        '<div class="sec-actions"><button class="btn-tool" id="pc-add">＋ в заказ</button></div>' +
        "</div></div>";
      bindHits($("part-card"));
      $("pc-add").onclick = function () { addToCart(part, name, 1); };
      /* Карточка — панель поверх всей страницы, шапку она закрывает
         целиком. Без своей кнопки закрытия из неё не выйти иначе как
         «Назад», а это не всегда очевидно. */
      $("pc-close").onclick = function () { history.back(); };
      busy(false);
      show("part");
    }).catch(function () { busy(false); });
  }

  /* Развёрнутая часть карточки детали: паспорт из EPC (масса, габариты,
     кратность упаковки, группа скидки, рекомендация по запасу), цена по
     обоим базисам, цепочка замен и фотографии. В таблице позиций то же
     самое — но в одну ячейку на колонку; здесь полностью, ради этого
     карточку и открывают. */
  function supplyBlocks(part) {
    var s = supplyOf(part);
    var kb = partInfo(part);
    var out = "";
    if (kb) {
      var rows = [
        ["Наименование", kb.ru || kb.en || ""],
        ["По-китайски", kb.zh || ""],
        ["Обозначение", kb.spec || ""],
        ["Масса, кг", kb.kg || ""],
        ["Габариты, мм", kb.mm || ""],
        ["Минимальная партия", kb.mpq || ""],
        ["Группа скидки", kb.dg || ""],
        ["Рекомендация по запасу", kb.stock || ""],
        ["Единица", kb.unit || ""]
      ].filter(function (r) { return r[1] !== "" && r[1] != null; });
      var tags = [];
      if (kb.maint) tags.push("деталь ТО");
      if (kb.wear) tags.push("быстроизнашивающаяся");
      if (kb.special) tags.push("особый заказ");
      out += "<h3>Паспорт детали</h3>" +
        (tags.length ? '<p class="sub">' + esc(tags.join(" · ")) + "</p>" : "") +
        '<table class="stock-table">' + rows.map(function (r) {
          return "<tr><td>" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>";
        }).join("") + "</table>";
      if (kb.ph && kb.ph.length) {
        out += "<h3>Фотографии</h3><div class=\"photo-strip\">" +
          kb.ph.map(function (src) {
            return '<img class="photo" src="' + esc(src) + '" alt="' + esc(part) + '" loading="lazy">';
          }).join("") + "</div>";
      }
    }
    if (s && s.p) {
      out += "<h3>Цена по прайс-листу</h3>" +
        '<p class="sub an-note">' + esc(priceNote()) + "</p>" +
        '<table class="stock-table"><tr><th>Базис поставки</th>' +
        '<th class="num">рублей без НДС</th></tr>' +
        (s.p.b1 != null ? '<tr><td>' + esc(BASIS.b1) + '</td><td class="num">' +
          money(s.p.b1) + "</td></tr>" : "") +
        (s.p.b2 != null ? '<tr><td>' + esc(BASIS.b2) + '</td><td class="num">' +
          money(s.p.b2) + "</td></tr>" : "") +
        "</table>" +
        (s.p.n ? '<p class="sub">В прайсе записана как «' + esc(s.p.n) + "».</p>" : "");
    }
    out += chainList(s);
    if (s && s.note) {
      out += "<h3>Примечание завода</h3><p class=\"sub\">" + esc(s.note) + "</p>";
    }
    if (!out) {
      out = '<p class="sub">По этому номеру ничего сверх состава узлов нет: ' +
        "ни паспорта в выгрузке, ни цены в прайс-листе, ни пометки о замене.</p>";
    }
    return out;
  }

  /* Паспорт детали лежит теми же шардами, что индекс и цены: класть в
     оболочку все девятнадцать тысяч паспортов ради одной открытой
     карточки незачем. */
  var infoCache = {};

  function loadInfoFor(part) {
    var name = norm(part).slice(0, 2) || "__";
    return loadScript("p:" + name, "data/kb/p-" + name + ".js")
      .then(function (shard) {
        Object.keys(shard).forEach(function (k) { infoCache[k] = shard[k]; });
        return shard;
      })
      .catch(function () { return {}; });
  }

  function partInfo(part) { return infoCache[part] || null; }

  function priceNote() {
    var meta = window.SUPPLY_META || {};
    return "Прайс-лист " + ((meta.sources || {}).price || "LiuGong") +
      ". Цены даны на два базиса поставки; какой из них применим, " +
      "зависит от предприятия-получателя.";
  }

  /* Цепочка замен. Пометка о замене приходит из EPC словами, в примечании
     к позиции, поэтому рядом с номером всегда стоит расшифровка того, что
     именно завод сказал: односторонняя замена и взаимозаменяемость — не
     одно и то же, и ошибка здесь стоит неверно заказанной детали. */
  function chainList(s) {
    var links = (s && s.c) || [], flags = (s && s.f) || [];
    if (!links.length && !flags.length) return "";
    var out = "<h3>Замены и состояние номера</h3>";
    if (flags.length) {
      out += '<p class="sub an-note">' + flags.map(function (code) {
        var t = codeText(code);
        return esc(t.tag) + " — " + esc(t.full);
      }).join("<br>") + "</p>";
    }
    out += links.map(function (l) {
      var t = codeText(l.code);
      var side = l.dir === "old" ? "прежний номер"
        : l.dir === "new" ? "текущий номер" : "равнозначный номер";
      var no = l.d || l.n;
      return '<div class="analog-row">' + (l.x
        ? '<span class="pn">' + esc(no) + "</span>"
        : '<span class="pn pn-link" data-part="' + esc(no) + '">' + esc(no) + "</span>") +
        '<span class="at" title="' + esc(t.full) + '">' + esc(t.tag) + "</span>" +
        '<span class="sub">' + esc(side) +
        (l.x ? " · в каталоге этого номера нет" : "") + "</span></div>";
    }).join("");
    return out;
  }

  // ------------------------------------------------------- проверка списка --

  var checkRows = [];

  function runCheck() {
    var raw = $("check-input").value.split(/[\s,;]+/).filter(Boolean);
    if (!raw.length) return;
    busy(true);
    var keys = raw.map(norm);
    var shards = {};
    keys.forEach(function (k) { shards[k.slice(0, 2) || "__"] = 1; });
    Promise.all(Object.keys(shards).map(loadShard)).then(function (parts) {
      var all = {};
      parts.forEach(function (p) {
        Object.keys(p).forEach(function (k) { all[k] = p[k]; });
      });
      checkRows = raw.map(function (r, i) {
        var hits = all[keys[i]] || [];
        var books = {};
        hits.forEach(function (h) { books[h[0]] = 1; });
        return {
          asked: r,
          found: hits.length > 0,
          part: hits.length ? hits[0][3] : "",
          books: Object.keys(books),
          uses: hits.length
        };
      });
      $("check-results").innerHTML =
        '<table class="parts an-table check-results"><thead><tr>' +
        "<th>Номер из списка</th><th>Статус</th><th>Как записан в книге</th>" +
        "<th>Книг</th><th>Применений</th></tr></thead><tbody>" +
        checkRows.map(function (c) {
          return "<tr" + (c.found ? "" : ' class="st-consign"') + "><td>" + esc(c.asked) +
            "</td><td>" + (c.found ? "есть в каталоге" : "не найден") + "</td><td>" +
            esc(c.part) + "</td><td>" + (c.books.length || "") + "</td><td>" +
            (c.uses || "") + "</td></tr>";
        }).join("") + "</tbody></table>";
      busy(false);
    }).catch(function () { busy(false); });
  }

  // ------------------------------------------------------------------ парк --

  var fleetFilter = "";

  function openFleet() {
    var list = FLEET.filter(function (m) {
      return !fleetFilter || m.be === fleetFilter;
    });
    var withBook = list.filter(function (m) { return m.books.length; }).length;
    var exact = list.filter(function (m) { return m.fit === "vin"; }).length;
    $("fleet-lead").textContent = list.length + " " +
      plural(list.length, "машина", "машины", "машин") + ", каталог есть у " +
      withBook + " (из них выкачано по своему VIN — " + exact + "). " +
      "Щелчок по строке открывает каталог этой машины.";
    $("fleet-filters").innerHTML = ['', ].concat(sites()).map(function (s) {
      return '<button class="an-chip' + (fleetFilter === s ? " on" : "") +
        '" data-site="' + esc(s) + '">' + esc(s || "Все предприятия") + "</button>";
    }).join("");
    Array.prototype.forEach.call($("fleet-filters").querySelectorAll("[data-site]"), function (el) {
      el.onclick = function () { fleetFilter = el.getAttribute("data-site"); openFleet(); };
    });
    $("fleet-table").innerHTML = "<thead><tr>" +
      "<th>Предприятие</th><th>Парк</th><th>Модель</th><th>VIN</th>" +
      "<th>Гар. №</th><th>Год</th><th>КТГ план</th><th>Каталог</th></tr></thead><tbody>" +
      list.map(function (m, i) {
        var note = m.fit === "vin" ? "каталог по этому VIN"
          : m.fit === "model" ? "каталог той же модели"
          : "каталога нет";
        var title = m.fit === "vin"
          ? "Каталог выкачан из EPC по VIN этой машины — состав точный."
          : m.fit === "model"
          ? "Каталог выкачан по VIN другой машины той же модели. Исполнения " +
            "(materialNo) совпадают не всегда — состав может отличаться."
          : "Машины этой модели в выгрузке EPC нет.";
        return "<tr" + (m.books.length ? ' class="row-link" data-i="' + i + '"' : "") +
          "><td>" + esc(m.be) + "</td><td>" + esc(m.mvz) + "</td><td>" + esc(m.model) +
          "</td><td>" + esc(m.sn || "—") + "</td><td>" + esc(m.garage) + "</td><td>" +
          esc(m.year) + '</td><td class="num">' +
          (m.ktg === "" || m.ktg == null ? "—" : Math.round(m.ktg * 100) + " %") +
          '</td><td><span class="fit fit-' + esc(m.fit) + '" title="' + esc(title) + '">' +
          esc(note) + "</span></td></tr>";
      }).join("") + "</tbody>";
    Array.prototype.forEach.call($("fleet-table").querySelectorAll("[data-i]"), function (el) {
      el.onclick = function () {
        var m = list[parseInt(el.getAttribute("data-i"), 10)];
        selectBook(m.books[0], null, m);
      };
    });
    show("fleet");
  }

  // ----------------------------------------------------------------- заказ --

  var cart = [];
  try { cart = JSON.parse(localStorage.getItem("liugong_cart") || "[]"); } catch (e) { cart = []; }

  function saveCart() {
    try { localStorage.setItem("liugong_cart", JSON.stringify(cart)); } catch (e) { /* приватный режим */ }
    $("cart-count").textContent = cart.length;
  }

  function addToCart(part, name, qty) {
    var b = byCode[state.book];
    var found = cart.filter(function (c) {
      return c.part === part && c.book === (b ? b.code : "");
    })[0];
    if (found) found.qty += qty;
    else cart.push({ part: part, name: name, qty: qty, book: b ? b.code : "",
                     model: b ? b.model : "", unit: state.unit || "" });
    saveCart();
    renderCart();
  }

  function renderCart() {
    $("cart-body").innerHTML = cart.length
      ? cart.map(function (c, i) {
          return '<div class="cart-row"><div class="cart-no">' + esc(c.part) +
            '<span class="cart-sub">' + esc(c.model) + " · " + esc(c.unit) + "</span></div>" +
            '<div class="cart-name">' + esc(c.name) + "</div>" +
            '<input class="cart-qty" type="number" min="1" value="' + c.qty +
            '" data-i="' + i + '">' +
            '<button class="btn-plain" data-del="' + i + '">✕</button></div>';
        }).join("")
      : '<p class="sub">Заказ пуст.</p>';
    Array.prototype.forEach.call($("cart-body").querySelectorAll("[data-del]"), function (el) {
      el.onclick = function () {
        cart.splice(parseInt(el.getAttribute("data-del"), 10), 1);
        saveCart(); renderCart();
      };
    });
    Array.prototype.forEach.call($("cart-body").querySelectorAll(".cart-qty"), function (el) {
      el.onchange = function () {
        cart[parseInt(el.getAttribute("data-i"), 10)].qty = parseInt(el.value, 10) || 1;
        saveCart();
      };
    });
  }

  // -------------------------------------------------------------- выгрузки --

  function csv(rows, name) {
    var text = "﻿" + rows.map(function (r) {
      return r.map(function (v) {
        v = String(v == null ? "" : v);
        return /[";\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
      }).join(";");
    }).join("\r\n");
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
    a.download = name;
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  /* Строка снабжения для CSV — без разметки, только цифры и коды: цена по
     обоим базисам, состояние номера и цепочка замен. Те же данные, что в
     колонках таблицы, только для выгрузки. */
  function supplyRow(part) {
    var s = part && supplyOf(part);
    if (!s) return ["", "", "", ""];
    var flags = (s.f || []).map(function (c) { return codeText(c).tag; }).join("; ");
    var chain = (s.c || []).map(function (l) {
      return codeText(l.code).tag + " " + (l.d || l.n);
    }).join("; ");
    return [
      s.p && s.p.b1 != null ? s.p.b1 : "",
      s.p && s.p.b2 != null ? s.p.b2 : "",
      flags,
      chain
    ];
  }

  var SUPPLY_HEAD = ["Цена базис 1, ₽ без НДС", "Цена базис 2, ₽ без НДС",
                     "Состояние номера", "Замены"];

  function rowFlags(r) {
    var out = [];
    if (flag(r, F_KIT)) out.push("ремкомплект");
    if (flag(r, F_REMAN)) out.push("Reman");
    if (flag(r, F_NOORDER)) out.push("отдельно не поставляется");
    if (flag(r, F_FIT)) out.push("в исполнении книги");
    return out.join("; ");
  }

  function exportUnit() {
    if (!curUnit) return;
    var b = byCode[state.book];
    var rows = [["Каталог", "Модель", "Узел", "Название узла", "№ на чертеже",
                 "Номер детали", "Наименование", "Кол-во", "Примечание",
                 "Запас", "Кратность", "Признаки"].concat(SUPPLY_HEAD)];
    visibleRows(curUnit).forEach(function (r) {
      rows.push([b.code, b.model, curUnit.id, curUnit.t, r[0], r[1] || "",
                 r[2] || "", r[3] == null ? "" : r[3], r[4] || "", r[5] || "",
                 r[8] || "", rowFlags(r)].concat(supplyRow(r[1])));
    });
    csv(rows, "liugong-" + b.code + "-" + curUnit.id + ".csv");
  }

  function exportBook() {
    var b = byCode[state.book];
    if (!b || !confirm("Собрать все номера каталога " + b.model + "? Это " +
      num(b.lines) + " строк, займёт несколько секунд.")) return;
    busy(true);
    var units = unitsFlat.filter(function (u) { return u.g; });
    var rows = [["Каталог", "Модель", "Узел", "Название узла", "Номер сборки",
                 "№ на чертеже", "Номер детали", "Наименование", "Кол-во",
                 "Примечание", "Запас", "Кратность", "Признаки"].concat(SUPPLY_HEAD)];
    var i = 0;
    (function step() {
      if (i >= units.length) {
        csv(rows, "liugong-" + b.code + ".csv");
        busy(false);
        return;
      }
      var u = units[i++];
      loadUnit(b.code, u.id).then(function (p) {
        var parts = p.rows.map(function (r) { return r[1]; }).filter(Boolean);
        return loadSupplyFor(parts).then(function () {
          p.rows.forEach(function (r) {
            rows.push([b.code, b.model, p.id, p.t, p.r, r[0], r[1] || "", r[2] || "",
                       r[3] == null ? "" : r[3], r[4] || "", r[5] || "", r[8] || "",
                       rowFlags(r)].concat(supplyRow(r[1])));
          });
        });
      }).then(step, step);
    })();
  }

  // --------------------------------------------------------------- прочее --

  function renderLangSwitch() {
    Array.prototype.forEach.call(
      $("lang-switch").querySelectorAll("[data-lang]"), function (el) {
        el.classList.toggle("on", el.getAttribute("data-lang") === state.lang);
      });
  }

  /* Переключение языка перерисовывает то, что открыто, а таблицу перевода
     подтягивает по требованию — на «как в книге» она вообще не нужна. */
  function setLang(lang) {
    state.lang = lang;
    try { localStorage.setItem("liugong_lang", lang); } catch (e) { /* приватный режим */ }
    renderLangSwitch();
    var redraw = function () {
      renderPassport();
      renderTree($("tree-search").value);
      if (state.view === "unit" && state.unit) openUnit(state.unit, state.path, state.highlight);
      else if (state.view === "welcome") openWelcome();
    };
    if (lang === "en") redraw();
    else { busy(true); loadTranslate(lang).then(function () { busy(false); redraw(); }); }
  }

  function setTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem("liugong_theme", t); } catch (e) { /* приватный режим */ }
  }

  function wire() {
    $("theme-toggle").onclick = function () {
      setTheme(document.documentElement.getAttribute("data-theme") === "dark"
        ? "light" : "dark");
    };
    renderLangSwitch();
    Array.prototype.forEach.call(
      $("lang-switch").querySelectorAll("[data-lang]"), function (el) {
        el.onclick = function () { setLang(el.getAttribute("data-lang")); };
      });
    $("tree-search").oninput = function () { renderTree(this.value); };
    $("search").oninput = function () {
      var v = this.value;
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () { runSearch(v); }, 250);
    };
    $("search-clear").onclick = function () {
      $("search").value = ""; openWelcome();
    };
    $("show-fleet").onclick = openFleet;
    $("check-list").onclick = function () { show("check"); };
    $("check-run").onclick = runCheck;
    $("check-csv").onclick = function () {
      if (!checkRows.length) return;
      csv([["Номер из списка", "Статус", "Как записан", "Книг", "Применений"]].concat(
        checkRows.map(function (c) {
          return [c.asked, c.found ? "есть" : "не найден", c.part,
                  c.books.length, c.uses];
        })), "liugong-проверка-списка.csv");
    };
    $("go-back").onclick = function () { history.back(); };
    $("cart-toggle").onclick = function () {
      $("cart-panel").classList.toggle("hidden"); renderCart();
    };
    $("cart-close").onclick = function () { $("cart-panel").classList.add("hidden"); };
    $("cart-clear").onclick = function () { cart = []; saveCart(); renderCart(); };
    $("cart-print").onclick = function () { window.print(); };
    $("cart-csv").onclick = function () {
      csv([["Номер детали", "Наименование", "Кол-во", "Книга", "Модель", "Узел"]].concat(
        cart.map(function (c) { return [c.part, c.name, c.qty, c.book, c.model, c.unit]; })),
        "liugong-заказ.csv");
    };
    $("dl-unit").onclick = exportUnit;
    $("dl-book").onclick = exportBook;
    $("lightbox").onclick = function () { this.classList.add("hidden"); };
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (!$("lightbox").classList.contains("hidden")) {
          $("lightbox").classList.add("hidden");
          return;
        }
        if (!$("cart-panel").classList.contains("hidden")) {
          $("cart-panel").classList.add("hidden");
          return;
        }
        if (state.view === "part") history.back();
      }
    });
  }

  // ----------------------------------------------------------------- старт --

  function start() {
    if (!BOOKS.length) {
      document.body.innerHTML = '<div class="fatal">Список книг не загружен. ' +
        'Обновите страницу без кэша (Ctrl+F5).</div>';
      return;
    }
    wire();
    saveCart();
    fillHeader();
    /* Первый показ — база истории, а не шаг в ней: иначе один лишний
       history.pushState тут же встаёт перед стартовой страницей, и первый
       же «Назад» бьёт мимо, в документ без состояния. */
    restoring = true;
    var want = handoff();
    var first = (want && byCode[want.book]) ? want.book : booksOfSite("")[0].code;
    selectBook(first, function () {
      restoring = false;
      if (want && want.unit && findNode(want.unit)) openUnit(want.unit, [], want.part || null);
      else if (want && want.part) openPart(want.part);
      history.replaceState(snapshot(), "");
    });
  }

  /* Переход из базы знаний. Она — отдельная страница, и свой адрес
     каталог держит в history.state, а не в хеше, поэтому «открыть в
     каталоге» передаётся через localStorage и тут же вычитывается:
     оставленная запись при следующем заходе открыла бы не то. */
  function handoff() {
    try {
      var raw = localStorage.getItem("liugong_open");
      if (!raw) return null;
      localStorage.removeItem("liugong_open");
      return JSON.parse(raw);
    } catch (e) { return null; }
  }

  start();
})();
