use log::{error, warn};
use log::info;
use web3::types::ParityPendingTransactionFilter;
use std::{env, process};
use std::env::VarError;
use web3::api::EthSubscribe;
use web3::futures::{TryStreamExt};
use web3::transports::{WebSocket};
use web3::types::{TransactionId};
//use chrono::prelude::*;
fn get_node_endpoint() -> Result<String, VarError> {
        env::var("WSS_NODE_ENDPOINT")
      
}

#[tokio::main]

async fn main() -> web3::Result {
   
    env_logger::init();
   
      let sub_transport = WebSocket::new("wss://eth-rinkeby.alchemyapi.io/v2/OGYkQIyZYesg4jimDkMlgRBFdicYSn5S").await?;
    let web3 = web3::Web3::new(sub_transport);
    println!("web3{:?}",web3);
    let mut pending_transactions = web3.eth_subscribe().subscribe_new_pending_transactions().await?;
    let address="0x6cd5ca0be2d8edc2f229f6786a1a1d600b8a4e34";
    while let Some(pending_transaction_hash) = pending_transactions.try_next().await? {
        let pth = TransactionId::from(pending_transaction_hash);
        let res = web3.eth().transaction(pth).await;
          match res{
            Ok(opt_txn) => {
                match opt_txn{
                    None => { warn!("could not find transaction for now") },
                    Some(txn) => {
                       if txn.from.unwrap().to_string()==address{  
                        println!("{:?}", txn);
                        println!("{:?}", chrono::offset::Utc::now());}
                }
                }
            }
            Err(e) => error!("{:?}", e)
        }
    }
      Ok(())
}

