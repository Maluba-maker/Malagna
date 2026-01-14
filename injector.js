(function () {
  console.log("Pocket Option Signal Injector Started");

  const WS_URL = "wss://YOUR-BACKEND-URL/ws"; // Replace after backend deploy
  const ws = new WebSocket(WS_URL);

  ws.onopen = () => console.log("Connected to backend");

  let lastPrice = null;

  setInterval(() => {
    const el = document.querySelector(".open-time-number");
    if (!el) return;

    const price = parseFloat(el.innerText);
    if (!isNaN(price) && price !== lastPrice) {
      lastPrice = price;
      ws.send(price.toString());
      console.log("Sent price:", price);
    }
  }, 500);
})();
