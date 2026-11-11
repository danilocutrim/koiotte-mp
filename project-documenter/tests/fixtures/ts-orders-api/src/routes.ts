import express from "express";
import { SQSClient, SendMessageCommand } from "@aws-sdk/client-sqs";

const app = express();
const sqs = new SQSClient({ region: "us-east-1" });

app.post("/orders", async (req, res) => {
  const order = { id: Date.now(), ...req.body };
  await sqs.send(new SendMessageCommand({ QueueUrl: process.env.ORDERS_QUEUE_URL!, MessageBody: JSON.stringify(order) }));
  res.status(202).json(order);
});

app.get("/orders/:id", (req, res) => res.json({ id: req.params.id }));
