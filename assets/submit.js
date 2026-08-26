/* Builds a prefilled GitHub issue from the form, so nobody has to learn the
   issue form or git. The repository does the rest. */

(function () {
  "use strict";

  var REPO = "https://github.com/shanebivens/CrateDig";

  function issueUrl(template, title, fields) {
    var parts = ["template=" + encodeURIComponent(template)];
    if (title) parts.push("title=" + encodeURIComponent(title));
    Object.keys(fields).forEach(function (key) {
      var value = (fields[key] || "").trim();
      if (value) parts.push(key + "=" + encodeURIComponent(value));
    });
    return REPO + "/issues/new?" + parts.join("&");
  }

  function values(form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (element) {
      if (element.name) out[element.name] = element.value;
    });
    return out;
  }

  function firstEmptyRequired(form) {
    return Array.prototype.filter.call(form.elements, function (element) {
      return element.required && !element.value.trim();
    })[0];
  }

  function flash(form, message) {
    var box = form.querySelector(".form-error");
    if (!box) {
      box = document.createElement("p");
      box.className = "form-error";
      form.insertBefore(box, form.lastElementChild);
    }
    box.textContent = message;
  }

  var form = document.getElementById("form-track");
  if (!form) return;

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var missing = firstEmptyRequired(form);
    if (missing) {
      var label = missing.previousElementSibling.textContent
        .replace(" optional", "").trim().toLowerCase();
      flash(form, "Fill in " + label + " first.");
      missing.focus();
      return;
    }

    var data = values(form);
    window.open(issueUrl("submission.yml", "[pick] " + data.artist + " - " + data.track, {
      artist: data.artist,
      track: data.track,
      year: data.year,
      kind: data.kind,
      why: data.why,
      link: data.link
    }), "_blank", "noopener");
  });
})();
