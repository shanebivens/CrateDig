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

  function wire(form, build) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var missing = firstEmptyRequired(form);
      if (missing) {
        flash(form, "Fill in " + missing.previousElementSibling.textContent.replace(" optional", "").toLowerCase() + " first.");
        missing.focus();
        return;
      }
      var target = build(values(form));
      window.open(target, "_blank", "noopener");
    });
  }

  var trackForm = document.getElementById("form-track");
  if (trackForm) {
    wire(trackForm, function (data) {
      var title = "[pick] " + data.artist + " - " + data.track;
      return issueUrl("submission.yml", title, {
        artist: data.artist,
        track: data.track,
        year: data.year,
        kind: data.kind,
        why: data.why,
        link: data.link
      });
    });
  }

  var playlistForm = document.getElementById("form-playlist");
  if (playlistForm) {
    wire(playlistForm, function (data) {
      return issueUrl("playlist.yml", "[playlist] add me", {
        url: data.url,
        service: data.service,
        note: data.note,
        bio: data.bio
      });
    });
  }

  /* tabs */
  var tabs = [
    { button: document.getElementById("tab-track"), panel: document.getElementById("panel-track") },
    { button: document.getElementById("tab-playlist"), panel: document.getElementById("panel-playlist") }
  ];

  tabs.forEach(function (entry) {
    if (!entry.button) return;
    entry.button.addEventListener("click", function () {
      tabs.forEach(function (other) {
        var active = other === entry;
        other.button.classList.toggle("is-active", active);
        other.button.setAttribute("aria-selected", active ? "true" : "false");
        other.panel.classList.toggle("is-hidden", !active);
      });
    });
  });

  if (location.hash === "#playlist" && tabs[1].button) tabs[1].button.click();
})();
