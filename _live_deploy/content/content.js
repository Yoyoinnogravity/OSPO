(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function wordCount(text) {
    return (text || "").trim().split(/\s+/).filter(Boolean).length;
  }

  function buildToc() {
    var article = document.querySelector("[data-article]");
    var toc = document.querySelector("[data-toc]");
    if (!article || !toc) return;
    var heads = article.querySelectorAll("h2[id]");
    if (!heads.length) {
      toc.hidden = true;
      return;
    }
    var ol = document.createElement("ol");
    heads.forEach(function (h) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.textContent;
      li.appendChild(a);
      ol.appendChild(li);
    });
    toc.appendChild(ol);
  }

  function readingTime() {
    var el = document.querySelector("[data-reading-time]");
    var article = document.querySelector("[data-article]");
    if (!el || !article) return;
    var mins = Math.max(1, Math.round(wordCount(article.innerText) / 220));
    el.textContent = mins + " min read";
  }

  function lazyLoad() {
    var nodes = document.querySelectorAll("img[data-src], iframe[data-src]");
    if (!nodes.length) return;

    function load(el) {
      var src = el.getAttribute("data-src");
      if (!src) return;
      el.src = src;
      el.removeAttribute("data-src");
    }

    if (!("IntersectionObserver" in window)) {
      nodes.forEach(load);
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        load(entry.target);
        io.unobserve(entry.target);
      });
    }, { rootMargin: "200px 0px" });

    nodes.forEach(function (el) {
      io.observe(el);
    });
  }

  ready(function () {
    buildToc();
    readingTime();
    lazyLoad();
  });
})();
