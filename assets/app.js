/* CrateDig. Reads data/drops.json, which scripts/build.py writes. */

(function () {
  "use strict";

  var SERVICE_LABELS = {
    youtube: "YouTube",
    "youtube-music": "YT Music",
    spotify: "Spotify",
    "apple-music": "Apple",
    bandcamp: "Bandcamp",
    soundcloud: "SoundCloud",
    tidal: "Tidal",
    discogs: "Discogs",
    archive: "Archive"
  };

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  /* The stickers carry meaning a first visit has no way to know. */
  var KIND_TIPS = {
    obscure: "Obscure. It never surfaced.",
    forgotten: "Forgotten. Popular once, nobody plays it now.",
    sideways: "Sideways. Not rare, just never crossed your path.",
    unsorted: "Not sorted yet. Somebody decides at writeup time."
  };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function link(className, text, href) {
    var anchor = el("a", className, text);
    anchor.href = href;
    anchor.rel = "noopener";
    anchor.target = "_blank";
    return anchor;
  }

  /* Submissions come from strangers. Only http(s) goes near an href. */
  function safeHref(url) {
    return /^https?:\/\//i.test(String(url || "")) ? String(url) : "";
  }

  function formatDate(iso) {
    var parts = String(iso).split("-");
    if (parts.length !== 3) return iso;
    return parseInt(parts[2], 10) + " " +
      (MONTHS[parseInt(parts[1], 10) - 1] || parts[1]) + " " + parts[0];
  }

  function searchUrl(track) {
    return "https://music.youtube.com/search?q=" +
      encodeURIComponent(track.artist + " " + track.title);
  }

  /* Catalogue number, the way a label stamps a release: drop and position. */
  function catalogue(drop, index) {
    var number = String(drop.number || 0);
    while (number.length < 3) number = "0" + number;
    return "CD-" + number + "/" + (index + 1 < 10 ? "0" : "") + (index + 1);
  }

  function renderTrack(track, index, drop) {
    var sleeve = el("article", "sleeve");
    sleeve.appendChild(el("span", "sleeve-cat", catalogue(drop, index)));

    var kind = track.kind || "unsorted";
    var sticker = el("span", "sticker sticker--" + kind,
      kind === "unsorted" ? "not yet sorted" : kind);
    if (KIND_TIPS[kind]) {
      sticker.title = KIND_TIPS[kind];
      sticker.setAttribute("aria-label", KIND_TIPS[kind]);
    }
    sleeve.appendChild(sticker);

    sleeve.appendChild(el("h3", "sleeve-artist", track.artist));
    sleeve.appendChild(el("p", "sleeve-title", track.title));

    var meta = [];
    if (track.year) meta.push(track.year);
    meta.push(track.duration || "unmeasured");
    /* Pulled from the crate's own playlist, so nobody sent it in. */
    if (track.submitted_by && track.submitted_by !== "curator" && !track.pooled) {
      meta.push("sent in by " + track.submitted_by);
    }
    sleeve.appendChild(el("p", "sleeve-meta", meta.join("  ·  ")));

    if (track.why) sleeve.appendChild(el("p", "sleeve-note", track.why));

    var links = el("div", "sleeve-links");
    var radio = safeHref(track.radio);
    if (radio) {
      var fall = link("chip chip--fall", "Fall in", radio);
      fall.title = "Plays this, then keeps going into whatever it leads to";
      links.appendChild(fall);
    }

    var services = Object.keys(track.links || {}).filter(function (service) {
      if (!safeHref(track.links[service])) return false;
      /* Fall in already goes here, and without the radio it stops after one
         track, which is the opposite of the point. */
      if (radio && service === "youtube-music") return false;
      return true;
    });
    services.forEach(function (service) {
      links.appendChild(link("chip", SERVICE_LABELS[service] || service,
        safeHref(track.links[service])));
    });

    if (services.indexOf("spotify") === -1) {
      links.appendChild(link("chip chip--quiet", "Find on Spotify",
        safeHref(track.spotify_search) || searchUrl(track)));
    }
    if (!services.length && !radio) {
      links.appendChild(link("chip chip--quiet", "Search for it", searchUrl(track)));
    }

    sleeve.appendChild(links);
    return sleeve;
  }

  function renderDrop(drop, target) {
    target.className = "";
    target.innerHTML = "";

    var head = el("div", "crate-head");
    head.appendChild(el("span", "stamp",
      formatDate(drop.date) + "  ·  " + drop.tracks.length + " tracks"));

    /* The number is the headline. The blurb is a sentence and reads as
       shouting if it goes into the display face. */
    head.appendChild(el("h2", "crate-title", drop.title || "In the crate"));
    if (drop.blurb) head.appendChild(el("p", "crate-blurb", drop.blurb));

    /* Total runtime is a red herring here. You are not sitting through the
       drop, you are taking one track and letting its radio run. Each track
       carries its own length in the line under the title. */
    head.appendChild(el("p", "crate-cadence", "One a day until Monday."));

    /* No play-it-all link on purpose. Each track opens its own radio, and
       queueing the drop stops any of them from starting. */
    var play = el("div", "crate-play");
    Object.keys(drop.playlists || {}).forEach(function (service) {
      var href = safeHref(drop.playlists[service]);
      if (href) play.appendChild(link("chip", SERVICE_LABELS[service] || service, href));
    });
    if (play.childNodes.length) head.appendChild(play);

    target.appendChild(head);
    drop.tracks.forEach(function (track, index) {
      target.appendChild(renderTrack(track, index, drop));
    });
  }

  function renderArchive(drops, target) {
    target.className = "";
    target.innerHTML = "";
    if (!drops.length) {
      target.className = "empty";
      target.textContent = "Nothing behind this one yet. The next drop lands Monday.";
      return;
    }
    drops.forEach(function (drop) {
      var row = el("div", "back-row");
      row.appendChild(el("b", null, drop.title));
      row.appendChild(el("span", null, formatDate(drop.date)));
      row.appendChild(el("span", null, drop.tracks.length + " tracks"));
      target.appendChild(row);
    });
  }

  function renderCredit(people, target) {
    if (!people || !people.length) return;
    var line = el("p", "credit", "Brought back so far by " +
      people.map(function (person) {
        return person.handle + (person.picks > 1 ? " (" + person.picks + ")" : "");
      }).join(", ") + ".");
    target.appendChild(line);
  }

  function fail(message) {
    var latest = document.getElementById("latest");
    latest.className = "empty";
    latest.textContent = message;
    var archive = document.getElementById("archive");
    archive.className = "empty";
    archive.textContent = "";
  }

  fetch("data/drops.json", { cache: "no-cache" })
    .then(function (response) {
      if (!response.ok) throw new Error(response.status);
      return response.json();
    })
    .then(function (data) {
      var drops = data.drops || [];
      if (!drops.length) {
        fail("The crate is empty. The first drop lands Monday.");
        return;
      }
      renderDrop(drops[0], document.getElementById("latest"));
      renderArchive(drops.slice(1), document.getElementById("archive"));
      renderCredit(data.contributors, document.getElementById("credit"));
    })
    .catch(function () {
      fail("Could not open the crate. Run scripts/build.py to rebuild data/drops.json.");
    });
})();
