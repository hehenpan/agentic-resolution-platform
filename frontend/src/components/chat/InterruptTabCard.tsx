import React, { useState } from 'react';
import { AlertCircle, Send, CheckCircle2, UserCheck, PackageSearch, FileText, RotateCcw, PlusCircle } from 'lucide-react';
import type { WebHumanInputRequestedData } from '../../types/chat';

interface InterruptTabCardProps {
  requestData: WebHumanInputRequestedData;
  onSubmit: (payload: Record<string, unknown>, displayContent?: string) => void;
  disabled?: boolean;
}

const REASON_OPTIONS = [
  { value: 'change_of_mind', label: 'Change of Mind' },
  { value: 'damaged', label: 'Damaged Product' },
  { value: 'wrong_item', label: 'Wrong Item Received' },
  { value: 'not_as_described', label: 'Not as Described' },
  { value: 'late_delivery', label: 'Late Delivery' },
];

const CONDITION_OPTIONS = [
  { value: 'unopened', label: 'Unopened' },
  { value: 'opened', label: 'Opened' },
  { value: 'used', label: 'Used' },
  { value: 'damaged', label: 'Damaged' },
];

export const InterruptTabCard: React.FC<InterruptTabCardProps> = ({
  requestData,
  onSubmit,
  disabled = false,
}) => {
  const schemaId = requestData?.request?.schema_id || '';
  const prompt = requestData?.request?.prompt || 'Human-in-the-Loop input required.';
  
  // Single field state for simple interrupts
  const [inputValue, setInputValue] = useState('');

  // Multi-field state for create_return_request
  const [orderId, setOrderId] = useState('');
  const [customerId, setCustomerId] = useState('');
  const [reasonCode, setReasonCode] = useState('damaged');
  const [itemCondition, setItemCondition] = useState('opened');
  const [reasonText, setReasonText] = useState('');

  const [submitted, setSubmitted] = useState(false);

  const isGetUser = schemaId.includes('get_user');
  const isGetOrders = schemaId.includes('get_orders');
  const isGetOrderDetails = schemaId.includes('get_order_details');
  const isGetReturnsByOrder = schemaId.includes('get_returns_by_order');
  const isGetReturnsByCustomer = schemaId.includes('get_returns_by_customer');
  const isCreateReturn = schemaId.includes('create_return_request');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    setSubmitted(true);
    let payload: Record<string, unknown>;
    let displayContent: string;

    if (isCreateReturn) {
      const orderIdNum = parseInt(orderId.trim(), 10);
      const customerIdNum = parseInt(customerId.trim(), 10);
      payload = {
        order_id: isNaN(orderIdNum) ? orderId.trim() : orderIdNum,
        customer_id: isNaN(customerIdNum) ? customerId.trim() : customerIdNum,
        reason_code: reasonCode,
        item_condition: itemCondition,
        reason_text: reasonText.trim() || undefined,
      };
      displayContent = `[Submitted Form] Order ID: ${orderId.trim()}, Customer ID: ${customerId.trim()}, Reason: ${reasonCode}, Condition: ${itemCondition}`;
    } else if (isGetReturnsByCustomer) {
      const customerIdNum = parseInt(inputValue.trim(), 10);
      payload = { customer_id: isNaN(customerIdNum) ? inputValue.trim() : customerIdNum };
      displayContent = `[Submitted Form] Customer ID: ${inputValue.trim()}`;
    } else if (isGetOrderDetails || isGetReturnsByOrder) {
      const orderIdNum = parseInt(inputValue.trim(), 10);
      payload = { order_id: isNaN(orderIdNum) ? inputValue.trim() : orderIdNum };
      displayContent = `[Submitted Form] Order ID: ${inputValue.trim()}`;
    } else {
      payload = { email: inputValue.trim() };
      displayContent = `[Submitted Form] Customer Email: ${inputValue.trim()}`;
    }

    onSubmit(payload, displayContent);
  };

  const getHeaderTitle = () => {
    if (isGetUser) return 'Action Required: Customer Lookup Interrupt';
    if (isGetOrders) return 'Action Required: Customer Orders Interrupt';
    if (isGetOrderDetails) return 'Action Required: Order Details Interrupt';
    if (isGetReturnsByOrder) return 'Action Required: Returns by Order Interrupt';
    if (isGetReturnsByCustomer) return 'Action Required: Returns by Customer Interrupt';
    if (isCreateReturn) return 'Action Required: Create Return Request Interrupt';
    return 'Action Required: Human Input Interrupt';
  };

  const isSubmitDisabled = () => {
    if (disabled) return true;
    if (isCreateReturn) {
      return !orderId.trim() || !customerId.trim() || !reasonCode;
    }
    return !inputValue.trim();
  };

  return (
    <div className="mt-3 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-foreground glass-panel space-y-3 animate-fade-in shadow-lg shadow-amber-500/5 max-w-lg">
      {/* Header */}
      <div className="flex items-center space-x-2 text-amber-400 font-semibold text-sm">
        {isGetUser ? (
          <UserCheck className="w-4 h-4 text-amber-400 shrink-0" />
        ) : isGetOrders ? (
          <PackageSearch className="w-4 h-4 text-amber-400 shrink-0" />
        ) : isGetOrderDetails ? (
          <FileText className="w-4 h-4 text-amber-400 shrink-0" />
        ) : isGetReturnsByOrder ? (
          <RotateCcw className="w-4 h-4 text-amber-400 shrink-0" />
        ) : isCreateReturn ? (
          <PlusCircle className="w-4 h-4 text-amber-400 shrink-0" />
        ) : (
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
        )}
        <span>{getHeaderTitle()}</span>
      </div>

      {/* Prompt / Instructions */}
      <p className="text-xs text-muted-foreground leading-relaxed">{prompt}</p>

      {/* Tabs / Form Section */}
      {!submitted ? (
        <form onSubmit={handleSubmit} className="space-y-3 pt-1">
          {isCreateReturn ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col space-y-1">
                  <label htmlFor="return-order-id" className="text-xs font-medium text-amber-300/90">
                    Order ID <span className="text-rose-400">*</span>
                  </label>
                  <input
                    id="return-order-id"
                    type="number"
                    required
                    value={orderId}
                    onChange={(e) => setOrderId(e.target.value)}
                    placeholder="e.g. 88412"
                    disabled={disabled}
                    className="w-full px-3 py-2 text-xs bg-slate-900 border border-amber-500/40 rounded-xl text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all font-medium shadow-inner"
                  />
                </div>
                <div className="flex flex-col space-y-1">
                  <label htmlFor="return-customer-id" className="text-xs font-medium text-amber-300/90">
                    Customer ID <span className="text-rose-400">*</span>
                  </label>
                  <input
                    id="return-customer-id"
                    type="number"
                    required
                    value={customerId}
                    onChange={(e) => setCustomerId(e.target.value)}
                    placeholder="e.g. 1001"
                    disabled={disabled}
                    className="w-full px-3 py-2 text-xs bg-slate-900 border border-amber-500/40 rounded-xl text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all font-medium shadow-inner"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {/* Reason Code Select Dropdown */}
                <div className="flex flex-col space-y-1">
                  <label htmlFor="return-reason-code" className="text-xs font-medium text-amber-300/90">
                    Reason Code <span className="text-rose-400">*</span>
                  </label>
                  <select
                    id="return-reason-code"
                    required
                    value={reasonCode}
                    onChange={(e) => setReasonCode(e.target.value)}
                    disabled={disabled}
                    className="w-full px-3 py-2 text-xs bg-slate-900 border border-amber-500/40 rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all font-medium shadow-inner cursor-pointer"
                  >
                    {REASON_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value} className="bg-slate-900 text-slate-100">
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Item Condition Select Dropdown */}
                <div className="flex flex-col space-y-1">
                  <label htmlFor="return-item-condition" className="text-xs font-medium text-amber-300/90">
                    Item Condition <span className="text-rose-400">*</span>
                  </label>
                  <select
                    id="return-item-condition"
                    required
                    value={itemCondition}
                    onChange={(e) => setItemCondition(e.target.value)}
                    disabled={disabled}
                    className="w-full px-3 py-2 text-xs bg-slate-900 border border-amber-500/40 rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all font-medium shadow-inner cursor-pointer"
                  >
                    {CONDITION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value} className="bg-slate-900 text-slate-100">
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Reason Explanation Text */}
              <div className="flex flex-col space-y-1">
                <label htmlFor="return-reason-text" className="text-xs font-medium text-amber-300/90">
                  Reason Explanation
                </label>
                <input
                  id="return-reason-text"
                  type="text"
                  value={reasonText}
                  onChange={(e) => setReasonText(e.target.value)}
                  placeholder="e.g. Outer box crushed during delivery"
                  disabled={disabled}
                  className="w-full px-3 py-2 text-xs bg-slate-900 border border-amber-500/40 rounded-xl text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all font-medium shadow-inner"
                />
              </div>
            </div>
          ) : (
            <div className="flex flex-col space-y-1.5">
              <label htmlFor="interrupt-input-field" className="text-xs font-medium text-amber-300/90">
                {isGetReturnsByCustomer
                  ? 'Customer ID'
                  : isGetOrderDetails || isGetReturnsByOrder
                  ? 'Order ID'
                  : 'Customer Email Address'}{' '}
                <span className="text-rose-400">*</span>
              </label>
              <input
                id="interrupt-input-field"
                type={isGetReturnsByCustomer || isGetOrderDetails || isGetReturnsByOrder ? 'number' : 'email'}
                required
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={
                  isGetReturnsByCustomer
                    ? 'e.g. 1001'
                    : isGetOrderDetails || isGetReturnsByOrder
                    ? 'e.g. 88412'
                    : 'e.g. customer@example.com'
                }
                disabled={disabled}
                className="w-full px-3.5 py-2.5 text-xs bg-slate-900 border border-amber-500/40 rounded-xl text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all font-medium shadow-inner"
              />
            </div>
          )}

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-muted-foreground/80 italic">
              Tip: You can submit via this tab form or type in the chat box.
            </span>

            <button
              type="submit"
              disabled={isSubmitDisabled()}
              className="inline-flex items-center space-x-1.5 px-4 py-1.5 bg-amber-500 hover:bg-amber-600 active:scale-95 disabled:opacity-50 text-slate-950 font-semibold text-xs rounded-xl shadow-md transition-all shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Commit Input</span>
            </button>
          </div>
        </form>
      ) : (
        <div className="flex items-center space-x-2 text-emerald-400 text-xs py-1">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>Input committed successfully. Resuming Agent execution...</span>
        </div>
      )}
    </div>
  );
};
