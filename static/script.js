const messages = document.getElementById("messages");
const MAX_MESSAGES = 100;
let ws;
let reconnectInterval = 1000;
let wakeLock = null;

async function requestWakeLock() {
  try {
    if ("wakeLock" in navigator) {
      wakeLock = await navigator.wakeLock.request("screen");

      // Listen for the lock being released (e.g., if the user switches tabs)
      wakeLock.addEventListener("release", () => {
        wakeLock = null;
      });
    }
  } catch (err) {
    console.error(`${err.name}, ${err.message}`);
  }
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onmessage = function (event) {
    try {
      const data = JSON.parse(event.data);

      if (data.type === "status") {
        const dot = document.getElementById("status-dot");
        if (data.status === "connected") {
          dot.style.backgroundColor = "#00ff00"; // Green
          requestWakeLock();
        } else {
          dot.style.backgroundColor = "red";
        }
        return; // Stop processing since this isn't a chat message
      }

      const isAtBottom =
        Math.abs(
          window.innerHeight + window.scrollY - document.body.offsetHeight,
        ) <= 50;
      const messageLine = document.createElement("div");
      messageLine.className = "message-line";

      const profilePic = document.createElement("img");
      profilePic.className = "profile-pic";
      profilePic.src =
        data.authorImage ||
        "https://www.gstatic.com/youtube/img/creator/no_profile_img.png";

      const contentWrapper = document.createElement("div");
      contentWrapper.className = "content-wrapper";

      const authorSpan = document.createElement("span");
      authorSpan.className = "author";
      authorSpan.textContent = data.author || "Guest";

      const textSpan = document.createElement("span");
      textSpan.className = "text";

      renderSafeMessage(textSpan, data.message || "");

      contentWrapper.appendChild(authorSpan);
      contentWrapper.appendChild(textSpan);

      messageLine.appendChild(profilePic);
      messageLine.appendChild(contentWrapper);

      messages.appendChild(messageLine);

      while (messages.children.length > MAX_MESSAGES) {
        messages.removeChild(messages.firstChild);
      }

      if (isAtBottom) {
        window.scrollTo(0, document.body.scrollHeight);
      }
    } catch (err) {
      console.error("Error processing message:", err);
    }
  };

  ws.onclose = function () {
    setTimeout(connect, reconnectInterval);
  };

  ws.onerror = function () {
    ws.close();
  };
}

function renderSafeMessage(container, message) {
  // Create a temporary element to parse the HTML string
  const temp = document.createElement("div");
  temp.innerHTML = message;

  // If no child nodes, it's just plain text or empty
  if (temp.childNodes.length === 0 && message) {
    container.appendChild(document.createTextNode(message));
    return;
  }

  // Iterate through child nodes to safely transfer text and emojis
  Array.from(temp.childNodes).forEach((node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      container.appendChild(document.createTextNode(node.textContent));
    } else if (node.nodeType === Node.ELEMENT_NODE && node.tagName === "IMG") {
      // Transfer only the src and height to a new img element
      const img = document.createElement("img");
      img.className = "emoji";
      img.src = node.getAttribute("src");
      container.appendChild(img);
    }
  });
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    requestWakeLock();
  }
});

connect();
requestWakeLock();
