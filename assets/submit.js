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

  /* ---- fill the rest in from the link -------------------------------- */

  /* Upload titles are a mess. Strip the parts that are never the song. */
  var NOISE = /\s*[\(\[][^)\]]*(official|video|audio|lyric|visuali[sz]er|hd|hq|4k|remaster|full album|m\/v|explicit|audio only)[^)\]]*[\)\]]/gi;

  function tidy(text) {
    return String(text || "").replace(NOISE, "").replace(/\s{2,}/g, " ").trim();
  }

  function oembedUrl(link) {
    var host;
    try {
      host = new URL(link).hostname.toLowerCase().replace(/^www\./, "");
    } catch (error) {
      return null;
    }
    if (host === "youtube.com" || host === "music.youtube.com" || host === "youtu.be") {
      return "https://www.youtube.com/oembed?format=json&url=" + encodeURIComponent(link);
    }
    if (host === "open.spotify.com" || host === "spotify.com") {
      return "https://open.spotify.com/oembed?url=" + encodeURIComponent(link);
    }
    if (host === "soundcloud.com") {
      return "https://soundcloud.com/oembed?format=json&url=" + encodeURIComponent(link);
    }
    return null;   /* Bandcamp and the rest publish nothing to read */
  }

  /* Returns {artist, title} with either possibly empty. */
  function readOembed(data, link) {
    var raw = String(data.title || "");
    var author = String(data.author_name || "");

    if (link.indexOf("soundcloud.com") !== -1) {
      var by = raw.lastIndexOf(" by ");
      if (by > 0) return { artist: raw.slice(by + 4).trim(), title: tidy(raw.slice(0, by)) };
      return { artist: "", title: tidy(raw) };
    }

    if (link.indexOf("spotify.com") !== -1) {
      return { artist: "", title: tidy(raw) };   /* Spotify gives no artist */
    }

    /* YouTube. An auto-generated upload names the artist in the channel. */
    if (/\s-\sTopic$/.test(author)) {
      return { artist: author.replace(/\s-\sTopic$/, "").trim(), title: tidy(raw) };
    }
    var clean = tidy(raw);
    var dash = clean.indexOf(" - ");
    if (dash > 0) {
      return { artist: clean.slice(0, dash).trim(), title: clean.slice(dash + 3).trim() };
    }
    return { artist: author, title: clean };
  }

  function say(message) {
    var box = document.getElementById("lookup-note");
    if (box) box.textContent = message;
  }

  var lastLooked = "";

  function lookup(form) {
    var link = form.link.value.trim();
    if (!link || link === lastLooked) return;
    lastLooked = link;

    var endpoint = oembedUrl(link);
    if (!endpoint) {
      say(musicHost(link)
        ? "That site does not publish track details, so fill the next two in yourself."
        : "");
      return;
    }

    say("Reading the link.");
    fetch(endpoint)
      .then(function (response) {
        if (!response.ok) throw new Error(response.status);
        return response.json();
      })
      .then(function (data) {
        var found = readOembed(data, link);
        var filled = [];
        if (found.artist && !form.artist.value.trim()) {
          form.artist.value = found.artist;
          filled.push("artist");
        }
        if (found.title && !form.track.value.trim()) {
          form.track.value = found.title;
          filled.push("track");
        }
        if (filled.length) {
          say("Filled in the " + filled.join(" and ") +
              " from the link. Fix anything that looks wrong, upload titles lie.");
        } else if (found.artist || found.title) {
          say("Read the link. Left what you had typed alone.");
        } else {
          say("Nothing readable there, so fill the next two in yourself.");
        }
      })
      .catch(function () {
        say("Could not read that link. Fill the next two in yourself.");
      });
  }

  var form = document.getElementById("form-track");
  if (!form) return;

  form.link.addEventListener("change", function () { lookup(form); });
  form.link.addEventListener("blur", function () { lookup(form); });
  form.link.addEventListener("paste", function () {
    window.setTimeout(function () { lookup(form); }, 0);
  });

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
