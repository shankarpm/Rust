const ethers = require('ethers');
async function start() {
const provider = new ethers.providers.WebSocketProvider("ws://localhost:8546");
provider.on('pending', async (mempooltx) =>{
await provider.getTransaction(mempooltx).then(async (txdata) => {
if ((txdata != null && txdata['to'] == address)) {
console.log(txdata);
console.log(http://Date.now())
}
});
});
}
start();