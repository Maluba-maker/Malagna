(function () {
  console.log("Pocket Option Signal Injector started");

  const STREAMLIT_URL = "https://malagna.streamlit.app/";

  let lastPrice = null;

  function sendPrice(price) {
    const url = `${STREAMLIT_URL}?price=${price}`;
    fetch(url, { mode: "no-cors" });
  }

  setInterval(() => {
    const el = document.querySelector(".open-time-number");
    if (!el) return;

    const text = el.innerText || el.textContent;
    const price = parseFloat(text);

    if (!isNaN(price) && price !== lastPrice) {
      lastPrice = price;
      sendPrice(price);
      console.log("Sent price:", price);
    }
  }, 500);
})();
