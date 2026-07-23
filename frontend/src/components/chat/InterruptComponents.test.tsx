import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { InterruptTabCard } from './InterruptTabCard';
import { UserInfoCard } from './UserInfoCard';
import { OrdersCard } from './OrdersCard';
import { OrderDetailsCard } from './OrderDetailsCard';
import type { WebHumanInputRequestedData } from '../../types/chat';

describe('Interrupt and Card Components', () => {
  it('renders InterruptTabCard and handles submit', () => {
    const onSubmit = vi.fn();
    const requestData: WebHumanInputRequestedData = {
      event_id: 'evt_1',
      kind: 'agent.human_input_requested',
      thread_id: 'thread_1',
      run_id: 'run_1',
      interrupt_id: 'intr_1',
      request: {
        prompt: 'Please enter customer email to look up user information.',
        schema_id: 'human_input.get_user.v1',
      },
    };

    render(<InterruptTabCard requestData={requestData} onSubmit={onSubmit} />);

    expect(screen.getByText(/Customer Email Address/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Please enter customer email to look up user information./i)
    ).toBeInTheDocument();

    const input = screen.getByRole('textbox') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'customer@example.com' } });

    const submitBtn = screen.getByRole('button', { name: /Commit Input/i });
    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledWith(
      { email: 'customer@example.com' },
      '[Submitted Form] Customer Email: customer@example.com'
    );
  });

  it('renders InterruptTabCard for get_order_details and submits order_id', () => {
    const onSubmit = vi.fn();
    const requestData: WebHumanInputRequestedData = {
      event_id: 'evt_details_1',
      kind: 'agent.human_input_requested',
      thread_id: 'thread_1',
      run_id: 'run_1',
      interrupt_id: 'intr_details_1',
      request: {
        prompt: 'Please enter positive Order ID to look up order details.',
        schema_id: 'human_input.get_order_details.v1',
      },
    };

    render(<InterruptTabCard requestData={requestData} onSubmit={onSubmit} />);

    expect(screen.getByText('Order ID')).toBeInTheDocument();

    const input = screen.getByRole('spinbutton') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '88412' } });

    const submitBtn = screen.getByRole('button', { name: /Commit Input/i });
    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledWith(
      { order_id: 88412 },
      '[Submitted Form] Order ID: 88412'
    );
  });

  it('renders UserInfoCard with customer details', () => {
    const userData = {
      exists: true,
      user_id: 1001,
      email: 'alex@example.com',
      user_name: 'Alex Customer',
    };

    render(<UserInfoCard data={userData} />);

    expect(screen.getByText('E-Commerce User Profile')).toBeInTheDocument();
    expect(screen.getByText('#1001')).toBeInTheDocument();
    expect(screen.getByText('alex@example.com')).toBeInTheDocument();
    expect(screen.getByText('Alex Customer')).toBeInTheDocument();
  });

  it('renders OrdersCard with order list', () => {
    const ordersData = {
      customer_email: 'alex@example.com',
      orders: [
        {
          order_id: 88412,
          user_id: 1001,
          email: 'alex@example.com',
          status: 1,
          total_amount: 199.99,
          created_ts: 1700000000,
        },
      ],
    };

    render(<OrdersCard data={ordersData} />);

    expect(screen.getByText('Customer Order History')).toBeInTheDocument();
    expect(screen.getByText(/Order #88412/i)).toBeInTheDocument();
    expect(screen.getByText('PAID')).toBeInTheDocument();
    expect(screen.getByText('199.99')).toBeInTheDocument();
  });

  it('renders OrderDetailsCard with items table', () => {
    const orderDetailsData = {
      exists: true,
      order: {
        order_id: 88412,
        user_id: 1001,
        email: 'alex@example.com',
        status: 1,
        total_amount: 199.99,
        created_ts: 1753236000,
      },
      items: [
        {
          item_id: 1,
          sku_id: 501,
          sku_code: 'SKU-PRO-01',
          name: 'Wireless Noise-Canceling Headphones',
          quantity: 1,
          price: 149.99,
        },
      ],
    };

    render(<OrderDetailsCard data={orderDetailsData} />);

    expect(screen.getByText('Order Details')).toBeInTheDocument();
    expect(screen.getByText('#88412')).toBeInTheDocument();
    expect(screen.getByText('Wireless Noise-Canceling Headphones')).toBeInTheDocument();
    expect(screen.getByText('SKU-PRO-01')).toBeInTheDocument();
    expect(screen.getByText('$149.99')).toBeInTheDocument();
  });
});
