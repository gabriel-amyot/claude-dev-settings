# Design: event ticketing platform (draft v1)

## Context

A regional theatre group sells tickets for 30 venues. Most days are quiet. When a popular show opens sales, 20,000 people try to buy in the first ten minutes. Seats must never be sold twice. Two developers maintain the system. The board wants to add new payment providers next year.

## Architecture characteristics

All of these are critical: performance, scalability, elasticity, availability, reliability, security, maintainability, testability, deployability, usability, interoperability, extensibility.

## Decision

We will build 14 microservices (one per database table: Seat, Venue, Show, Order, Payment, Customer, Discount, ...). All services share one PostgreSQL database. The Order service calls Seat, Payment and Customer synchronously over REST for each purchase.

We chose microservices because it is the modern standard and scales.

## Governance

Code review will make sure the services stay decoupled.
