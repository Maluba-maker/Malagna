(function () {
  console.log("Signal injector running...");

  function sendPrice(price) {
    fetch("http://localhost:8501", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ price: price })
    }).catch(err => console.log("Send failed:", err));
  }

  setInterval(() => {
    // TEMP: fake price for testing
    const fakePrice = Math.random() * 100;
    sendPrice(fakePrice);
  }, 1000);
})();
