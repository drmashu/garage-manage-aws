import { Handler, Context } from "aws-lambda";
import { DynamoDBClient, DynamoDBClientConfig } from '@aws-sdk/client-dynamodb';
import {
  DynamoDBDocumentClient,
  UpdateCommand,
  UpdateCommandInput,
} from '@aws-sdk/lib-dynamodb'

class GarageEvent {
    ShutterPosition: number = 0;
    ShutterState: number = 0;
    LightState: number = 0;
    FanState:  number = 0;
    GarageId: string = '';
}

const config: DynamoDBClientConfig = {};
const dbClient = new DynamoDBClient(config);
const documentClient = DynamoDBDocumentClient.from(dbClient);

export const handler: Handler<GarageEvent, object> = async (event:GarageEvent, context: Context) => {

  console.log(JSON.stringify(event, undefined, 2));
  try {
    const command = new UpdateCommand({
      TableName: 'lambda-garages-7HDMLSDDW3TR',
      Key: {
        GarageId: event.GarageId,
      },
      UpdateExpression: 'set ShutterPosition = :w, ShutterState = :x, LightState = :y, FanState = :z',
      ExpressionAttributeValues: {
        ':w': event.ShutterPosition,
        ':x': event.ShutterState,
        ':y': event.LightState,
        ':z': event.FanState,
      },
    } as UpdateCommandInput);
    const output = await documentClient.send(command);
    console.log('SUCCESS (update item):', output);
  } catch (err) {
    console.log('ERROR:', err)
  }

  return {};
};
