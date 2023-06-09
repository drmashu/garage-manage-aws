import { Handler, Context } from "aws-lambda";
import { DynamoDBClient, DynamoDBClientConfig } from '@aws-sdk/client-dynamodb';
import {
  DynamoDBDocumentClient,
  GetCommand,
} from '@aws-sdk/lib-dynamodb'

const config: DynamoDBClientConfig = {};
const dbClient = new DynamoDBClient(config);
const documentClient = DynamoDBDocumentClient.from(dbClient);

class HttpEvent {
  pathParameters: PathParameters = new PathParameters();
}
class PathParameters {
  garageId: string = '';
}

export const handler: Handler<HttpEvent, object> = async (event: HttpEvent, context:Context) => {
  // Log the event argument for debugging and for use in local development.
  console.log(JSON.stringify(event, undefined, 2));
  console.log("GetGarageState : " + JSON.stringify(event, undefined, 2));
  let result:any = {};
  try {
    const command = new GetCommand({
      TableName: 'lambda-garages-7HDMLSDDW3TR',
      Key: {
        GarageId: event.pathParameters.garageId,
      },
    })
    const output = await documentClient.send(command)
    console.log('SUCCESS (get item):', output)
    result = output.Item;
  } catch (err) {
    console.log('ERROR:', err)
  }
  return result;
};
