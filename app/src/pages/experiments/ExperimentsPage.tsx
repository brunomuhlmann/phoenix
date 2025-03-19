import React, { Suspense, useState, useEffect } from "react";
import { Outlet, useLoaderData } from "react-router";
import { Flex, Loading, Text } from "@phoenix/components";
import { fetchQuery, graphql } from "react-relay";
import RelayEnvironment from "@phoenix/RelayEnvironment";
import { experimentsLoaderQuery, experimentsLoaderQuery$data } from "./__generated__/experimentsLoaderQuery.graphql";
import { ExperimentsTable } from "./ExperimentsTable";

export function ExperimentsPage() {
  const { datasetId } = useLoaderData() as { datasetId: string };
  const [data, setData] = useState<experimentsLoaderQuery$data | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const result = await fetchQuery<experimentsLoaderQuery>(
          RelayEnvironment,
          graphql`
            query ExperimentsPageQuery($id: GlobalID!) {
              dataset: node(id: $id) {
                id
                ... on Dataset {
                  ...ExperimentsTableFragment
                }
              }
            }
          `,
          { id: datasetId }
        ).toPromise();

        setData(result as experimentsLoaderQuery$data);
      } catch (error) {
        console.error("Error loading experiments:", error);
      } finally {
        setTimeout(() => setIsLoading(false), 500);
      }
    };

    loadData();
  }, [datasetId]);

  if (isLoading || !data) {
    return (
      <Flex direction="column" alignItems="center" justifyContent="center" height="100%" padding="size-400">
        <Loading size="L" />
        <Text marginTop="size-200">Loading experiments...</Text>
      </Flex>
    );
  }

  return (
    <>
      <ExperimentsTable dataset={data.dataset} />
      <Suspense>
        <Outlet />
      </Suspense>
    </>
  );
}
