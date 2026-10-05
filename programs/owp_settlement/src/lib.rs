use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, TransferChecked};

declare_id!("2sWkMoDppGvjHemtT2kxbbrGoMRLT4p6jocsBG1H8nKk");

#[program]
pub mod owp_settlement {
    use super::*;

    pub fn fund_order(ctx: Context<FundOrder>, job_id: [u8; 32], work_hash: [u8; 32],
        provider: Pubkey, verifier: Pubkey, amount: u64, deadline: i64) -> Result<()> {
        let customer = ctx.accounts.customer.key();
        require!(job_id != [0; 32] && work_hash != [0; 32], EscrowError::InvalidDigest);
        require!(amount > 0 && deadline > Clock::get()?.unix_timestamp, EscrowError::InvalidTerms);
        require!(provider != Pubkey::default() && verifier != Pubkey::default()
            && customer != provider && customer != verifier && provider != verifier,
            EscrowError::InvalidRoles);
        let order = &mut ctx.accounts.order;
        order.customer = customer;
        order.provider = provider;
        order.verifier = verifier;
        order.mint = ctx.accounts.mint.key();
        order.job_id = job_id;
        order.work_hash = work_hash;
        order.bundle_hash = [0; 32];
        order.acceptance_hash = [0; 32];
        order.amount = amount;
        order.deadline = deadline;
        order.status = OrderStatus::Funded;
        order.bump = ctx.bumps.order;
        token::transfer_checked(CpiContext::new(ctx.accounts.token_program.key(), TransferChecked {
            from: ctx.accounts.source.to_account_info(),
            mint: ctx.accounts.mint.to_account_info(),
            to: ctx.accounts.vault.to_account_info(),
            authority: ctx.accounts.customer.to_account_info(),
        }), amount, ctx.accounts.mint.decimals)
    }

    pub fn submit_delivery(ctx: Context<SubmitDelivery>, bundle_hash: [u8; 32]) -> Result<()> {
        let order = &mut ctx.accounts.order;
        require!(order.status == OrderStatus::Funded, EscrowError::InvalidState);
        require!(Clock::get()?.unix_timestamp < order.deadline, EscrowError::Expired);
        require!(bundle_hash != [0; 32], EscrowError::InvalidDigest);
        order.bundle_hash = bundle_hash;
        order.status = OrderStatus::Delivered;
        Ok(())
    }

    pub fn accept_and_release(ctx: Context<Release>, work_hash: [u8; 32], bundle_hash: [u8; 32], acceptance_hash: [u8; 32]) -> Result<()> {
        let order = &ctx.accounts.order;
        require!(order.status == OrderStatus::Delivered, EscrowError::InvalidState);
        require!(work_hash == order.work_hash && bundle_hash == order.bundle_hash, EscrowError::EvidenceMismatch);
        require!(acceptance_hash != [0; 32], EscrowError::InvalidDigest);
        let bump = [order.bump];
        let seeds: &[&[u8]] = &[b"order", order.customer.as_ref(), &order.job_id, &bump];
        token::transfer_checked(CpiContext::new_with_signer(ctx.accounts.token_program.key(), TransferChecked {
            from: ctx.accounts.vault.to_account_info(),
            mint: ctx.accounts.mint.to_account_info(),
            to: ctx.accounts.destination.to_account_info(),
            authority: order.to_account_info(),
        }, &[seeds]), order.amount, ctx.accounts.mint.decimals)?;
        let order = &mut ctx.accounts.order;
        order.acceptance_hash = acceptance_hash;
        order.status = OrderStatus::Settled;
        Ok(())
    }

    pub fn reject_delivery(ctx: Context<RejectDelivery>) -> Result<()> {
        require!(ctx.accounts.order.status == OrderStatus::Delivered, EscrowError::InvalidState);
        ctx.accounts.order.status = OrderStatus::Disputed;
        Ok(())
    }

    pub fn refund_expired(ctx: Context<Refund>) -> Result<()> {
        require!(ctx.accounts.order.status == OrderStatus::Funded, EscrowError::InvalidState);
        require!(Clock::get()?.unix_timestamp >= ctx.accounts.order.deadline, EscrowError::NotExpired);
        refund(&ctx.accounts)?;
        ctx.accounts.order.status = OrderStatus::Refunded;
        Ok(())
    }

    pub fn refund_mutual(ctx: Context<Refund>) -> Result<()> {
        require!(ctx.accounts.provider.is_signer, EscrowError::ProviderConsentRequired);
        require!(matches!(ctx.accounts.order.status, OrderStatus::Delivered | OrderStatus::Disputed), EscrowError::InvalidState);
        refund(&ctx.accounts)?;
        ctx.accounts.order.status = OrderStatus::Refunded;
        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(job_id: [u8; 32])]
pub struct FundOrder<'info> {
    #[account(mut)]
    pub customer: Signer<'info>,
    #[account(init, payer = customer, space = 8 + Order::INIT_SPACE,
        seeds = [b"order", customer.key().as_ref(), job_id.as_ref()], bump)]
    pub order: Account<'info, Order>,
    #[account(init, payer = customer, seeds = [b"vault", order.key().as_ref()], bump,
        token::mint = mint, token::authority = order)]
    pub vault: Account<'info, TokenAccount>,
    pub mint: Account<'info, Mint>,
    #[account(mut, token::mint = mint, token::authority = customer)]
    pub source: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SubmitDelivery<'info> {
    pub provider: Signer<'info>,
    #[account(mut, seeds = [b"order", order.customer.as_ref(), order.job_id.as_ref()],
        bump = order.bump, has_one = provider)]
    pub order: Account<'info, Order>,
}

#[derive(Accounts)]
pub struct Release<'info> {
    pub customer: Signer<'info>,
    pub verifier: Signer<'info>,
    #[account(mut, seeds = [b"order", customer.key().as_ref(), order.job_id.as_ref()],
        bump = order.bump, has_one = customer, has_one = verifier, has_one = mint)]
    pub order: Account<'info, Order>,
    #[account(mut, seeds = [b"vault", order.key().as_ref()], bump,
        token::mint = mint, token::authority = order)]
    pub vault: Account<'info, TokenAccount>,
    pub mint: Account<'info, Mint>,
    #[account(mut, token::mint = mint, constraint = destination.owner == order.provider @ EscrowError::WrongDestination)]
    pub destination: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct RejectDelivery<'info> {
    pub customer: Signer<'info>,
    #[account(mut, seeds = [b"order", customer.key().as_ref(), order.job_id.as_ref()], bump = order.bump, has_one = customer)]
    pub order: Account<'info, Order>,
}

#[derive(Accounts)]
pub struct Refund<'info> {
    pub customer: Signer<'info>,
    /// CHECK: Bound to the frozen provider by has_one. Mutual refunds explicitly require is_signer.
    pub provider: UncheckedAccount<'info>,
    #[account(mut, seeds = [b"order", customer.key().as_ref(), order.job_id.as_ref()],
        bump = order.bump, has_one = customer, has_one = provider, has_one = mint)]
    pub order: Account<'info, Order>,
    #[account(mut, seeds = [b"vault", order.key().as_ref()], bump,
        token::mint = mint, token::authority = order)]
    pub vault: Account<'info, TokenAccount>,
    pub mint: Account<'info, Mint>,
    #[account(mut, token::mint = mint, token::authority = customer)]
    pub destination: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

fn refund(accounts: &Refund<'_>) -> Result<()> {
    let order = &accounts.order;
    let bump = [order.bump];
    let seeds: &[&[u8]] = &[b"order", order.customer.as_ref(), &order.job_id, &bump];
    token::transfer_checked(CpiContext::new_with_signer(accounts.token_program.key(), TransferChecked {
        from: accounts.vault.to_account_info(),
        mint: accounts.mint.to_account_info(),
        to: accounts.destination.to_account_info(),
        authority: order.to_account_info(),
    }, &[seeds]), order.amount, accounts.mint.decimals)
}

#[account]
#[derive(InitSpace)]
pub struct Order {
    pub customer: Pubkey,
    pub provider: Pubkey,
    pub verifier: Pubkey,
    pub mint: Pubkey,
    pub job_id: [u8; 32],
    pub work_hash: [u8; 32],
    pub bundle_hash: [u8; 32],
    pub acceptance_hash: [u8; 32],
    pub amount: u64,
    pub deadline: i64,
    pub status: OrderStatus,
    pub bump: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum OrderStatus {
    Funded,
    Delivered,
    Disputed,
    Settled,
    Refunded,
}

#[error_code]
pub enum EscrowError {
    #[msg("Digest must not be all zero")]
    InvalidDigest,
    #[msg("Amount must be positive and deadline must be in the future")]
    InvalidTerms,
    #[msg("Customer, provider and verifier must be distinct nonzero identities")]
    InvalidRoles,
    #[msg("Order state does not permit this instruction")]
    InvalidState,
    #[msg("Delivery deadline has passed")]
    Expired,
    #[msg("Work or delivery digest does not match the frozen order")]
    EvidenceMismatch,
    #[msg("Token destination is not owned by the frozen provider")]
    WrongDestination,
    #[msg("Undelivered order has not expired")]
    NotExpired,
    #[msg("Provider signature is required for a mutual refund")]
    ProviderConsentRequired,
}
