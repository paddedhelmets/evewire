# Epic: Market Orders & History

**Type**: Epic
**Priority**: P1

View character market orders, order history, and order slot utilization. Includes outstanding buy/sell totals, expired/canceled orders tracking, and identification of available order slots.

## Child Tasks (Beads)

### 1. Market Order List View
Display current market orders for all characters with filtering and sorting:
- Buy vs sell orders
- Order status (active, expired, cancelled, fulfilled)
- Item type, station, price, remaining volume
- Outstanding buy/sell totals per character
- Orders expiring soon warnings

### 2. Order Slot Utilization
Track and display market order slot usage:
- Show available order slots per character (based on skills)
- Warning when slots are nearly full
- Quick filter to show characters with available slots

### 3. Order History
View historical market orders:
- Expired/cancelled/fulfilled orders
- Date range filtering
- Export to CSV

### 4. Order Sync Reliability
Ensure ESI order sync handles edge cases:
- Duplicate order detection
- Order state transitions (active -> expired/closed)
- Pagination for large order histories

---

# Epic: Wallet Journal & Transactions

**Type**: Epic
**Priority**: P1

View character wallet journal entries and transaction history. Includes balance tracking, income/expense analysis by category, and financial summary views.

## Child Tasks (Beads)

### 1. Wallet Journal View
Display wallet journal entries with pagination:
- All journal types (bounty, market escrow, contract price, etc.)
- Date range filtering
- Amount formatting (ISK)
- Transaction type badges
- Click to view related details

### 2. Transaction History
View market buy/sell transactions:
- Transaction type (buy/sell)
- Item name and quantity
- Price and total
- Station/location
- Date/time

### 3. Balance Tracking
Show wallet balance over time:
- Historical balance chart
- Current balance for all characters
- Balance change indicators (24h, 7d, 30d)

### 4. Income/Expense Summary
Aggregate financial data by category:
- Income breakdown (bounties, trading, contracts, etc.)
- Expense breakdown (purchases, taxes, fees)
- Net profit/loss calculation
- Character comparison views

### 5. Journal Sync Reliability
Ensure ESI journal sync handles:
- Pagination for large histories
- Duplicate detection
- Missing page recovery

---

# Epic: Industry Jobs & History

**Type**: Epic
**Priority**: P1

View character industry jobs, job history, and manufacturing slot utilization. Includes active jobs tracking, completed jobs history, and identification of available job slots.

## Child Tasks (Beads)

### 1. Active Industry Jobs
Display currently running industry jobs:
- Job type (manufacturing, research, copying, etc.)
- Blueprint and output item
- Station/facility location
- Progress bar (time remaining)
- Start/end time

### 2. Job Slot Utilization
Track industry job slot usage:
- Show available job slots per character
- Display job cap based on skills
- Warning when slots are nearly full
- Filter for characters with available slots

### 3. Job History
View completed/failed/cancelled jobs:
- Job status filtering
- Date range selection
- Output quantity vs success chance
- Material cost tracking

### 4. Blueprint Details
Show blueprint information for jobs:
- Blueprint ME/TE levels
- Runs remaining (for BPCs)
- Location of blueprint
- Linked to job history

### 5. Job Sync Reliability
Ensure ESI industry job sync handles:
- Pagination
- Completed job detection
- Job state transitions
- Blueprint lookup errors
