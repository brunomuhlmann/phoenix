import { css } from "@emotion/react";
import { ReactNode, useMemo } from "react";

import {
  HelpTooltip,
  TooltipTrigger,
  TriggerWrap,
} from "@arizeai/components";

import { Flex, Heading, Text } from "@phoenix/components";
import { floatFormatter, formatInt } from "@phoenix/utils/numberFormatUtils";

type MetricKey = "precision" | "recall" | "f1" | "support";

type ClassMetrics = {
  precision: number;
  recall: number;
  f1: number;
  support: number;
};

export type ClassificationReportData = {
  weightedAvg: ClassMetrics;
  perClass: Array<{
    className: string;
    metrics: ClassMetrics;
  }>;
};

const metricOrder: MetricKey[] = ["precision", "recall", "f1", "support"];
const metricHeaderLabels: Record<MetricKey, string> = {
  precision: "P",
  recall: "R",
  f1: "F1",
  support: "S",
};

export type ClassificationReportTooltipProps = {
  children: ReactNode;
  classificationReport: ClassificationReportData | null | undefined;
  experimentName: string;
  metricKey: MetricKey;
  placement?: any;
};

export function ClassificationReportTooltip({
  children,
  classificationReport,
  experimentName,
  metricKey,
  placement = "bottom end",
}: ClassificationReportTooltipProps) {
  const formattedReport = useMemo<ClassificationReportData | null>(() => {
    if (!classificationReport) return null;
    return {
      weightedAvg: sanitizeMetrics(classificationReport.weightedAvg),
      perClass: classificationReport.perClass.map(({ className, metrics }) => ({
        className,
        metrics: sanitizeMetrics(metrics),
      })),
    };
  }, [classificationReport]);

  return (
    <TooltipTrigger 
      placement={placement} 
      delay={0}
      containerPadding={0}
    >
      <TriggerWrap>{children}</TriggerWrap>
      <HelpTooltip
        UNSAFE_style={{
          maxWidth: 'none',
          width: 'max-content',
        }}
      >
        <div css={tooltipContentStyles}>
          <Flex direction="column" gap="size-100">
            <Heading level={4} weight="heavy">
              Classification Report – {experimentName}
            </Heading>
            {formattedReport ? (
              <ClassificationReportTable
                metricKey={metricKey}
                report={formattedReport}
              />
            ) : (
              <Text size="S">Classification report unavailable.</Text>
            )}
          </Flex>
        </div>
      </HelpTooltip>
    </TooltipTrigger>
  );
}

type ClassificationReportTableProps = {
  metricKey: MetricKey;
  report: ClassificationReportData;
};

function ClassificationReportTable({
  metricKey,
  report,
}: ClassificationReportTableProps) {
  const { perClass, weightedAvg } = report;

  if (!perClass.length) {
    return <Text size="S">No per-class metrics available.</Text>;
  }

  return (
    <div css={tableContainerStyles}>
      <table css={tableStyles}>
        <thead>
          <tr>
            <th css={headerCellStyles}>Class</th>
            {metricOrder.map((key) => (
              <th
                key={key}
                css={[headerCellStyles, key === metricKey && highlightHeaderStyles]}
              >
                {metricHeaderLabels[key]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {perClass.map(({ className, metrics }) => (
            <tr key={className}>
              <td css={rowLabelCellStyles}>{className}</td>
              {metricOrder.map((key) => (
                <td
                  key={key}
                  css={[cellStyles, key === metricKey && highlightCellStyles]}
                >
                  {formatMetric(key, metrics[key])}
                </td>
              ))}
            </tr>
          ))}
          <tr>
            <td colSpan={metricOrder.length + 1} css={spacingRowStyles} />
          </tr>
          <tr>
            <td css={[rowLabelCellStyles, weightedLabelStyles]}>Weighted Avg</td>
            {metricOrder.map((key) => (
              <td
                key={key}
                css={[cellStyles, key === metricKey && highlightCellStyles]}
              >
                {formatMetric(key, weightedAvg[key])}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function formatMetric(metricKey: MetricKey, value: number) {
  if (metricKey === "support") {
    return formatInt(Math.round(value));
  }
  return floatFormatter(value);
}

function sanitizeMetrics(metrics: ClassMetrics): ClassMetrics {
  return {
    precision: safeNumber(metrics.precision),
    recall: safeNumber(metrics.recall),
    f1: safeNumber(metrics.f1),
    support: safeNumber(metrics.support),
  };
}

function safeNumber(value: number | null | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }
  return value;
}

const tableContainerStyles = css`
  overflow-x: auto;
`;

const tableStyles = css`
  width: 100%;
  border-collapse: collapse;
  font-size: var(--ac-global-font-size-75);
  white-space: nowrap;
`;

const headerCellStyles = css`
  padding: var(--ac-global-dimension-size-75)
    var(--ac-global-dimension-size-125);
  text-align: right;
  border-bottom: 1px solid var(--ac-global-color-gray-300, #d1d5db);
  background-color: var(--ac-global-color-gray-100, #f3f4f6);
  color: var(--ac-global-color-gray-900, #111827);

  &:first-of-type {
    text-align: left;
  }
`;

const cellStyles = css`
  padding: var(--ac-global-dimension-size-75)
    var(--ac-global-dimension-size-125);
  text-align: right;
  border-bottom: 1px solid var(--ac-global-color-gray-200, #e5e7eb);
`;

const rowLabelCellStyles = css`
  ${cellStyles};
  text-align: left;
  font-weight: 500;
`;

const weightedLabelStyles = css`
  font-weight: 600;
`;

const highlightCellStyles = css`
  font-weight: 600;
  background-color: rgba(37, 99, 235, 0.12);
`;

const highlightHeaderStyles = css`
  font-weight: 700;
  background-color: rgba(37, 99, 235, 0.2);
`;

const spacingRowStyles = css`
  padding: 0;
  height: var(--ac-global-dimension-size-100);
  border: none;
  background: transparent;
`;

const tooltipContentStyles = css`
  min-width: 600px;
  max-width: 800px;
  width: max-content;
`;

