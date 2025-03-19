import { LoaderFunctionArgs } from "react-router-dom";

export async function experimentsLoader(args: LoaderFunctionArgs) {
  const { datasetId } = args.params;
  return { datasetId };
}