/* Builds a prefilled GitHub issue from the form, so nobody has to learn the
   issue form or git. The repository does the rest. */

(function () {
  "use strict";

  var REPO = "https://github.com/shanebivens/CrateDig";

  /* Somewhere the track actually plays. Mirrors MUSIC_HOSTS in scripts/intake.py,
     so the form and the bot agree about what counts. */
  var MUSIC_HOSTS = [
    "youtube.com", "youtu.be", "open.spotify.com", "spotify.com",
    "bandcamp.com", "soundcloud.com", "music.apple.com", "itunes.apple.com",
    "tidal.com", "deezer.com", "discogs.com", "archive.org", "last.fm",
    "mixcloud.com", "audiomack.com", "hearthis.at", "jamendo.com"
  ];

  function musicHost(value) {
    var url;
    try {
      url = new URL(value.trim());
    } catch (error) {
      return false;
    }
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    var host = url.hostname.toLowerCase().replace(/^www\./, "");
    return MUSIC_HOSTS.some(function (known) {
      return host === known || host.slice(-(known.length + 1)) === "." + known;
    });
  }

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

    if (!musicHost(form.link.value)) {
      flash(form, "That link needs to point at a music site: YouTube, Spotify, "
        + "Bandcamp, SoundCloud, Apple Music, Tidal, Discogs or Archive.org.");
      form.link.focus();
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
