import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { InterruptTabCard } from './InterruptTabCard';
import { UserInfoCard } from './UserInfoCard';
import { OrdersCard } from './OrdersCard';
import { OrderDetailsCard } from './OrderDetailsCard';
import { ReturnsByOrderCard } from './ReturnsByOrderCard';
import { CreateReturnResultCard } from './CreateReturnResultCard';
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

  it('renders InterruptTabCard for create_return_request with reason_code dropdown', () => {
    const onSubmit = vi.fn();
    const requestData: WebHumanInputRequestedData = {
      event_id: 'evt_create_ret_1',
      kind: 'agent.human_input_requested',
      thread_id: 'thread_1',
      run_id: 'run_1',
      interrupt_id: 'intr_create_ret_1',
      request: {
        prompt: 'Please enter return details to create return request.',
        schema_id: 'human_input.create_return_request.v1',
      },
    };

    render(<InterruptTabCard requestData={requestData} onSubmit={onSubmit} />);

    expect(screen.getByText('Action Required: Create Return Request Interrupt')).toBeInTheDocument();
    expect(screen.getByLabelText(/Reason Code/i)).toBeInTheDocument();

    const orderIdInput = screen.getByLabelText(/Order ID/i) as HTMLInputElement;
    const customerIdInput = screen.getByLabelText(/Customer ID/i) as HTMLInputElement;
    const reasonCodeSelect = screen.getByLabelText(/Reason Code/i) as HTMLSelectElement;

    fireEvent.change(orderIdInput, { target: { value: '88412' } });
    fireEvent.change(customerIdInput, { target: { value: '1001' } });
    fireEvent.change(reasonCodeSelect, { target: { value: 'damaged' } });

    const submitBtn = screen.getByRole('button', { name: /Commit Input/i });
    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledWith(
      {
        order_id: 88412,
        customer_id: 1001,
        reason_code: 'damaged',
        item_condition: 'opened',
        reason_text: undefined,
      },
      '[Submitted Form] Order ID: 88412, Customer ID: 1001, Reason: damaged, Condition: opened'
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

  it('renders ReturnsByOrderCard with return details', () => {
    const returnsData = {
      order_id: 88412,
      return_request: {
        return_request_id: 9001,
        order_id: 88412,
        customer_id: 1001,
        status: 1,
        reason_code: 1,
        reason_text: 'Product arrived damaged.',
        item_condition: 3,
        requested_at: 1753236000,
        created_at: 1753236000,
        updated_at: 1753236000,
      },
    };

    render(<ReturnsByOrderCard data={returnsData} />);

    expect(screen.getByText(/Return Details for Order #88412/i)).toBeInTheDocument();
    expect(screen.getByText('#RET-9001')).toBeInTheDocument();
    expect(screen.getByText('APPROVED')).toBeInTheDocument();
    expect(screen.getByText('Damaged Product')).toBeInTheDocument();
  });

  it('renders CreateReturnResultCard on successful return request creation', () => {
    const createReturnData = {
      success: true,
      return_request: {
        return_request_id: 9901,
        order_id: 88412,
        customer_id: 1001,
        status: 0,
        reason_code: 1,
        reason_text: 'Damaged in transit.',
        item_condition: 1,
        requested_at: 1753236000,
        created_at: 1753236000,
        updated_at: 1753236000,
      },
      error_message: null,
    };

    render(<CreateReturnResultCard data={createReturnData} />);

    expect(screen.getByText('Return Request Created Successfully')).toBeInTheDocument();
    expect(screen.getByText('#RET-9901')).toBeInTheDocument();
    expect(screen.getByText('#88412')).toBeInTheDocument();
    expect(screen.getByText('Damaged Product')).toBeInTheDocument();
  });
});
