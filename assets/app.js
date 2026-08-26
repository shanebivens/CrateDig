/* CrateDig site. Reads data/drops.json, which scripts/build.py writes. */

(function () {
  "use strict";

  var SERVICE_LABELS = {
    youtube: "YouTube",
    "youtube-music": "YouTube Music",
    spotify: "Spotify",
    "apple-music": "Apple Music",
    bandcamp: "Bandcamp",
    soundcloud: "SoundCloud",
    tidal: "Tidal",
    discogs: "Discogs",
    archive: "Archive.org"
  };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function formatDate(iso) {
    var parts = String(iso).split("-");
    if (parts.length !== 3) return iso;
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var month = months[parseInt(parts[1], 10) - 1] || parts[1];
    return month + " " + parseInt(parts[2], 10) + ", " + parts[0];
  }

  function formatRuntime(seconds) {
    var minutes = Math.floor(seconds / 60);
    var rest = seconds % 60;
    return minutes + "m " + (rest < 10 ? "0" : "") + rest + "s";
  }

  function safeHref(url) {
    /* Submissions come from strangers. Only http(s) is allowed near an href. */
    return /^https?:\/\//i.test(String(url || "")) ? String(url) : "";
  }

  function searchUrl(track) {
    var query = track.artist + " " + track.title;
    return "https://music.youtube.com/search?q=" + encodeURIComponent(query);
  }

  function renderTrack(track, index) {
    var row = el("article", "track");
    row.appendChild(el("div", "track-number", String(index + 1).padStart(2, "0")));

    var body = el("div", "track-body");
    body.appendChild(el("p", "track-artist", track.artist));
    body.appendChild(el("h3", "track-title", track.title));

    var tags = el("div", "track-tags");
    if (track.kind) {
      tags.appendChild(el("span", "tag-kind " + track.kind, track.kind));
    }
    if (track.year) tags.appendChild(el("span", null, track.year));
    tags.appendChild(el("span", null, track.duration || "--:--"));
    if (track.submitted_by && track.submitted_by !== "curator") {
      tags.appendChild(el("span", null, "via " + track.submitted_by));
    }
    body.appendChild(tags);

    if (track.why) body.appendChild(el("p", "track-why", track.why));

    var links = el("div", "track-links");

    var radio = safeHref(track.radio);
    if (radio) {
      var hole = el("a", "is-radio", "Fall in");
      hole.href = radio;
      hole.rel = "noopener";
      hole.target = "_blank";
      hole.title = "Plays this, then keeps going into whatever it leads to";
      links.appendChild(hole);
    }

    var services = Object.keys(track.links || {});
    if (services.length && services.some(function (s) { return safeHref(track.links[s]); })) {
      services.forEach(function (service) {
        var href = safeHref(track.links[service]);
        if (!href) return;
        var anchor = el("a", null, SERVICE_LABELS[service] || service);
        anchor.href = href;
        anchor.rel = "noopener";
        anchor.target = "_blank";
        links.appendChild(anchor);
      });
    } else {
      var search = el("a", "is-search", radio ? "Find it elsewhere" : "Search for it");
      search.href = searchUrl(track);
      search.rel = "noopener";
      search.target = "_blank";
      links.appendChild(search);
    }
    body.appendChild(links);

    row.appendChild(body);
    return row;
  }

  function renderDrop(drop, target) {
    target.className = "";
    target.innerHTML = "";

    var head = el("div", "drop-head");
    var meta = el("div", "drop-meta");
    meta.appendChild(el("span", null, formatDate(drop.date)));
    meta.appendChild(el("span", null, drop.tracks.length + " tracks"));
    head.appendChild(meta);
    head.appendChild(el("h2", "drop-title", drop.title || "Drop"));
    if (drop.blurb) head.appendChild(el("p", "drop-blurb", drop.blurb));

    var runtime = el("div", "runtime");
    if (drop.unknown_durations) {
      runtime.textContent = drop.unknown_durations === drop.tracks.length
        ? "Runtime not measured yet"
        : formatRuntime(drop.seconds) + " so far, " + drop.unknown_durations + " track(s) unmeasured";
    } else if (drop.target_seconds) {
      runtime.textContent = formatRuntime(drop.seconds) +
        " of about " + Math.round(drop.target_seconds / 60) + "m";
      var bar = el("div", "runtime-bar");
      var fill = el("div", "runtime-fill");
      var pct = Math.min(100, Math.round((drop.seconds / drop.target_seconds) * 100));
      fill.style.width = pct + "%";
      bar.appendChild(fill);
      runtime.appendChild(bar);
    } else {
      runtime.textContent = formatRuntime(drop.seconds);
    }
    head.appendChild(runtime);

    var play = el("div", "play-row");
    var queue = safeHref(drop.queue_url);
    if (queue) {
      var all = el("a", "button button-play", "Play them back to back");
      all.href = queue;
      all.rel = "noopener";
      all.target = "_blank";
      play.appendChild(all);
    }
    Object.keys(drop.playlists || {}).forEach(function (service) {
      var href = safeHref(drop.playlists[service]);
      if (!href) return;
      var anchor = el("a", "button button-quiet button-play", SERVICE_LABELS[service] || service);
      anchor.href = href;
      anchor.rel = "noopener";
      anchor.target = "_blank";
      play.appendChild(anchor);
    });
    if (play.childNodes.length) head.appendChild(play);

    target.appendChild(head);

    drop.tracks.forEach(function (track, index) {
      target.appendChild(renderTrack(track, index));
    });
  }

  function renderArchive(drops, target) {
    target.className = "";
    target.innerHTML = "";
    if (!drops.length) {
      target.className = "archive-empty";
      target.textContent = "Nothing here yet. The next drop lands soon.";
      return;
    }
    drops.forEach(function (drop) {
      var item = el("div", "archive-item");
      item.appendChild(el("strong", null, drop.title || formatDate(drop.date)));
      item.appendChild(el("span", null, formatDate(drop.date)));
      item.appendChild(el("span", null, drop.tracks.length + " tracks"));
      target.appendChild(item);
    });
  }

  function renderContributors(people, target) {
    if (!people || !people.length) return;
    var box = el("p", "participants-list");
    box.appendChild(el("span", null, "Picks so far from: "));
    box.appendChild(document.createTextNode(
      people.map(function (person) {
        return person.handle + (person.picks > 1 ? " (" + person.picks + ")" : "");
      }).join(", ")
    ));
    target.appendChild(box);
  }

  function fail(message) {
    var latest = document.getElementById("latest-drop");
    latest.className = "archive-empty";
    latest.textContent = message;
    var archive = document.getElementById("archive-list");
    archive.className = "archive-empty";
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
        fail("No drops published yet.");
        return;
      }
      renderDrop(drops[0], document.getElementById("latest-drop"));
      renderArchive(drops.slice(1), document.getElementById("archive-list"));
      renderContributors(data.contributors, document.getElementById("participants"));
    })
    .catch(function () {
      fail("Could not load the drops. Run scripts/build.py to rebuild data/drops.json.");
    });
})();
