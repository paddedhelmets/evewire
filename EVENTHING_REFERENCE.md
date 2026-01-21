# EVEthing Reference for Epic Implementation

Reference notes from original EVEthing source code for implementing:
- Market Orders & History (ev-vqw)
- Wallet Journal & Transactions (ev-eli)
- Industry Jobs & History (ev-1d4)

## Existing Models (✓)

We already have these models in `core/character/models.py`:
- `MarketOrder` - orders table with ESI sync
- `WalletJournalEntry` - journal entries
- `WalletTransaction` - market transactions

## Missing Models

Need to create:
- `IndustryJob` - industry jobs tracking

---

## 1. Market Orders & History

### EVEthing Model Reference (`thing/models/marketorder.py`)

```python
class MarketOrder(models.Model):
    order_id = models.BigIntegerField(primary_key=True)
    station = models.ForeignKey(Station)
    item = models.ForeignKey(Item)
    character = models.ForeignKey(Character)
    corp_wallet = models.ForeignKey(CorpWallet, null=True, blank=True)

    creator_character_id = models.IntegerField(db_index=True)

    escrow = models.DecimalField(max_digits=14, decimal_places=2)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    total_price = models.DecimalField(max_digits=17, decimal_places=2)

    buy_order = models.BooleanField(default=False)
    volume_entered = models.IntegerField()
    volume_remaining = models.IntegerField()
    minimum_volume = models.IntegerField()
    issued = models.DateTimeField(db_index=True)
    expires = models.DateTimeField(db_index=True)
```

### Sync Pattern (`thing/tasks/marketorders.py`)

**Key logic:**
1. Fetch existing orders into `order_map`
2. Iterate ESI response:
   - If order exists: update if changed (issued, volume_remaining, escrow, price)
   - If order is active and new: add to `rows` list
3. Bulk create new orders
4. Find orders not seen in response → delete
5. Create events for completed/expired orders

**State tracking:**
- `orderState` = "0" means active
- Orders not returned are considered closed/expired

### Slot Calculation (EVE skill-based)

Market order slots depend on skills:
- `Trade` skill: +5 slots per level
- `Retail` skill: +4 slots per level
- `Wholesale` skill: +8 slots per level
- `Tycoon` skill: +16 slots per level
- Maximum: 5 + (5+4+8+16)*5 = 305 order slots

ESI doesn't provide slot count - must calculate from character skills.

---

## 2. Wallet Journal & Transactions

### EVEthing Model Reference (`thing/models/journalentry.py`)

```python
class JournalEntry(models.Model):
    character = models.ForeignKey(Character)
    corp_wallet = models.ForeignKey(CorpWallet, null=True, blank=True)

    date = models.DateTimeField(db_index=True)

    ref_id = models.BigIntegerField(db_index=True)  # Deduplication key
    ref_type = models.ForeignKey(RefType)  # Transaction type

    owner1_id = models.IntegerField()
    owner2_id = models.IntegerField()

    arg_name = models.CharField(max_length=128)
    arg_id = models.BigIntegerField()

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance = models.DecimalField(max_digits=17, decimal_places=2)
    reason = models.CharField(max_length=255)

    tax_corp = models.ForeignKey(Corporation, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2)
```

### Sync Pattern (`thing/tasks/walletjournal.py`)

**Pagination:**
- Use `rowCount` = 2560 (max per request)
- Use `fromID` for next page (walk backwards from newest)

**Deduplication:**
- `ref_id` is unique identifier
- Skip entries that already exist in database

**Key insight:** EVEthing only inserts NEW entries, never updates.

### RefType Categories

Common EVEthing ref types for categorization:
- Income: bounty, market escrow, contract price, corporation reward
- Expenses: market transaction, contract price, repairs, faction
- Trading: market buy/sell, broker fees, taxes
- Industry: industry job cost, manufacturing output

---

## 3. Industry Jobs & History

### EVEthing Model Reference (`thing/models/industryjob.py`)

```python
class IndustryJob(models.Model):
    # Activity types
    MANUFACTURING_ACTIVITY = 1
    RESEARCHING_TECHNOLOGY_ACTIVITY = 2  # TE Research
    RESEARCHING_TIME_ACTIVITY = 3
    RESEARCHING_MATERIAL_ACTIVITY = 4  # ME Research
    COPYING_ACTIVITY = 5
    DUPLICATING_ACTIVITY = 6
    REVERSE_ENGINEERING_ACTIVITY = 7
    INVENTION_ACTIVITY = 8

    # Status values
    ACTIVE_STATUS = 1
    PAUSED_STATUS = 2
    CANCELLED_STATUS = 102
    DELIVERED_STATUS = 104
    FAILED_STATUS = 105
    UNKNOWN_STATUS = 999

    character = models.ForeignKey(Character)
    corporation = models.ForeignKey(Corporation, blank=True, null=True)

    job_id = models.IntegerField()
    installer_id = models.IntegerField()

    system = models.ForeignKey(System)
    activity = models.IntegerField(choices=ACTIVITY_CHOICES)
    blueprint = models.ForeignKey(Blueprint)
    output_location_id = models.BigIntegerField()
    runs = models.IntegerField()
    team_id = models.BigIntegerField()
    licensed_runs = models.IntegerField()
    product = models.ForeignKey(Item, null=True, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES)
    duration = models.IntegerField()

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    pause_date = models.DateTimeField()
    completed_date = models.DateTimeField()
```

### Sync Pattern (`thing/tasks/industryjobs.py`)

**State transitions:**
- Update existing jobs if: dates changed, status changed, product changed
- Create events for status changes (especially non-active states)
- Set old active jobs to UNKNOWN if end_date passed 90 days ago and not seen in sync

**Activity type meanings:**
- 1: Manufacturing
- 2: Researching Technology (TE research - reduce time)
- 3: TE Research (same as 2)
- 4: Researching Material (ME research - reduce waste)
- 5: Copying (make BPCs from BPO)
- 6: Duplicating (legacy)
- 7: Reverse Engineering
- 8: Invention

### Slot Calculation

Industry job slots depend on skills:
- Manufacturing: `Industry` skill: +1 slot per level (max 5)
- Research/Invention: `Advanced Industry` skill: +1 slot per level (max 5)
- Per-facility limits (manufacturing lines, lab slots)

---

## 4. ESI Endpoints

| Feature | ESI Endpoint | Scope | Cache |
|---------|--------------|-------|-------|
| Market Orders | `GET /characters/{id}/orders/` | `esi-markets.read_character_orders.v1` | 1h |
| Order History | `GET /characters/{id}/orders/history/` | `esi-markets.read_character_orders.v1` | 1h |
| Wallet Journal | `GET /characters/{id}/wallet/journal/` | `esi-wallet.read_character_wallet.v1` | 1h |
| Wallet Transactions | `GET /characters/{id}/wallet/transactions/` | `esi-wallet.read_character_wallet.v1` | 1h |
| Industry Jobs | `GET /characters/{id}/industry/jobs/` | `esi-industry.read_character_jobs.v1` | 5m |

---

## 5. What NOT to Implement

EVEthing had business logic we explicitly DON'T want:
- Trade analytics (profit/loss calculations)
- Market advice (what to buy/sell)
- Manufacturing calculators
- PI optimization
- Trade campaign tracking

Focus on: **data viewing, slot utilization, historical tracking**.
